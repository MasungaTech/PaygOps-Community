import json
from datetime import date, datetime

from flask.globals import request
from sales_system.leads.models.lead import Lead
from shared.helpers.db_helpers import TypeClassBase
from pony import orm
from core_system.core_entities import db
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from shared.api_helpers.client_helpers.json_serialization_helpers import serialize_data_to_json, deserialize_json_data
from shared.api_helpers.client_helpers.uuid_generation_helpers import generate_uuid
from messages_system.services.message_service import MessageService
import config

class TransactionRequestType(TypeClassBase):
    change_offer = 'change_offer'
    collect_cash = 'collect_cash'
    default = 'default'
    deregister = 'deregister'
    give_delay = 'give_delay'
    give_discount = 'give_discount'
    registration = 'registration'
    reverse_repayment = 'reverse_repayment'
    swap_device = 'swap_device'
    sync_activation = 'sync_activation'
    undo_default = 'undo_default'
    cancel = 'cancel'
    pause = 'pause'
    resume = 'resume'


class TransactionRequest(db.Entity, ModelDefinitionMixin):
    id = orm.PrimaryKey(int, auto=True)
    uuid = orm.Required(str, unique=True)
    time = orm.Required(datetime)
    type = orm.Required(str)
    request_data = orm.Optional(str)
    answer_data = orm.Optional(str)
    success = orm.Optional(bool)
    user = orm.Optional('User', column="user")
    client = orm.Optional('Client', column="client")
    device = orm.Optional('Device', column="device")
    offline = orm.Required(bool, default=False)

    modified_date = orm.Required(datetime, default=datetime.now, index=True)
    mobile_uuid = orm.Optional(str)

    @classmethod
    def get_model_definition(cls, op, human_answer=False, service=None):
        request_data = service.schema.copy() if service else {}
        request_data.update({
            "description": "Data sent with the transaction request",
            "value": lambda o: o.load_request_data(),
        })
        if 'properties' in request_data:
            request_data.update({
                "type": "object"
            })
        definition = {
            "properties": {
                "id": {
                    "type": "integer",
                    "example": 123,
                    "description": "The ID of the transaction",
                    "value": lambda o: o.id,
                },
                "uuid": {
                    "type": "string",
                    "example": "51f94e78-c6df-4edf-964b-72aec422d261",
                    "format": "uuid",
                    "description": "The UUID of the transaction",
                    "value": lambda o: o.uuid,
                },
                "time": {
                    "type": "string",
                    "example": datetime.now().isoformat(),
                    "description": "Time at which the transaction was requested",
                    "format": "date-time",
                    "value": lambda o: o.time,
                },
                "type": {
                    "description": "Type of the transaction",
                    "enum": TransactionRequestType.to_list(),
                    "example": service.type if service else TransactionRequestType.to_list()[0],
                    "type": "string",
                    "value": lambda o: o.type,
                },
                "request_data": request_data,
                "answer_data": {
                    "description": "Data returned as result of the transaction. It can contain extra data not listed here. ",
                    "type": "array",
                    "example": [{
                        "status": "TRANSACTION_ACTION_SUCCESSFUL",
                        "success": True,
                        "variable_1": "1",
                        "name_example": "The Name",
                        "amount_example": 23.40,
                    }],
                    "items": {
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "description": "Code representing a piece of information regarding the result of the transaction",
                            },
                            "success": {
                                "description": "Flag indicating whether the specific action within the transaction was successfull or not",
                                "type": "boolean",
                            },
                            "additionalProperties": True
                        },
                    },
                    "value": lambda o: o.load_answer_data(),
                },
                "success": {
                    "description": "Flag indicating whether the transaction was successfull or not",
                    "type": "boolean",
                    "example": True,
                    "value": lambda o: o.success,
                },
                "user": {
                    "description": "ID of the User that requested the transaction",
                    "type": "integer",
                    "example": 123,
                    "value": lambda o: o.user.id if o.user else None,
                },
                "client": {
                    "description": "ID of the client affected by the transaction",
                    "type": "integer",
                    "example": 123,
                    "value": lambda o: o.client.id if o.client else None,
                },
                "device": {
                    "description": "ID of the device affected by the transaction, if any",
                    "type": "integer",
                    "example": 123,
                    "value": lambda o: o.device.id if o.device else None,
                },
                "offline": {
                    "description": "Flag indicating whether the transaction was requested offline (with the mobile app) or online (either mobile/web/api)",
                    "type": "boolean",
                    "example": False,
                    "value": lambda o: o.offline,
                },
                "modified_date": {
                    "description": "Date and time of last modification of the transaction request",
                    "type": "string",
                    "format": "date-time",
                    "example": datetime.now().isoformat(),
                    "value": lambda o: o.modified_date,
                },
                "client_answer": {
                    "description": "Answer returned as result of the transaction request, adapted for the client. In can contain extra data not listed here. ",
                    "type": "array",
                    "example": [{
                        "status": "TRANSACTION_ACTION_SUCCESSFUL",
                        "success": True,
                        "variable_1": "1",
                        "name_example": "The Name",
                        "amount_example": 23.40,
                    }],
                    "items": {
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "description": "Code representing a piece of information regarding the result of the transaction",
                            },
                            "success": {
                                "description": "Flag indicating whether the specific action within the transaction was successfull or not",
                                "type": "boolean",
                            },
                            "additionalProperties": True
                        },
                    },
                    "value": lambda o: o.message_for_client,
                }
            },
            'view_required': [],
            'view_allowed': [],
            'edit_required': [],
            'edit_allowed': [],
            'create_allowed': [],
            'create_required': []
        }
        if human_answer:
            definition['properties'].update({
                "human_answer": {
                    "description": "Result of the transaction in a human readable version",
                    "type": "string",
                    "example": "This is the result of the transaction.",
                    "value": lambda o: o.get_human_answer(),
                }
            })
        return definition

    @property
    def message_for_client(self):
        answer = []
        for client_answer in json.loads(self.answer_data or "[]"):
            if client_answer['status'] in config.CUSTOMISABLE_MSGS_INFO:
                answer.append(client_answer)
        return answer

    def before_insert(self):
        if not self.mobile_uuid:
            self.mobile_uuid = generate_uuid()

    def store_answer_data(self, data):
        self.answer_data = serialize_data_to_json(data)

    def load_answer_data(self):
        return deserialize_json_data(self.answer_data)

    def store_request_data(self, data):
        self.request_data = serialize_data_to_json(data)

    def load_request_data(self):
        return deserialize_json_data(self.request_data)

    def get_dict(self, mobile=False):
        this_dict = self.to_dict()
        if mobile:
            this_dict['crmId'] = self.id
        this_dict['answer_data'] = self.load_answer_data()
        this_dict['request_data'] = self.load_request_data()
        return this_dict

    def get_human_answer(self):
        answer = MessageService.get_message(self.load_answer_data(), fallback_to_status=True, markdown_format=True)
        return answer
    
    def _get_affected_person(self):
        return (self.client or Lead.get(id=self.load_request_data().get('lead_id'))).person
    
    @property
    def modifiedDate(self):
        return self.modified_date
