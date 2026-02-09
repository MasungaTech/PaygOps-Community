from datetime import datetime
from jsonschema.exceptions import ValidationError
from pony import orm
from jsonschema import validate
from messages_system.services.message_service import MessageService
from payg_loan_system.contracts.services.addon_list_service import AddonListService
from payg_loan_system.devices.model.device import Device
from payg_loan_system.devices.non_payg_device_service import NonPAYGDeviceService
from payg_loan_system.transaction_requests.models import TransactionRequest
from payg_loan_system.contracts.services.contract_getter_service import \
    ContractGetterService
from shared.api_helpers.server_helpers.jwt_and_schema_verification import check_permissions_for_user
from shared.logger.loggers import LogAPI, Error
from shared.services.audit_log_service import AuditLogService


CONTRACT_REFERENCE_SCHEMA = {
    "type": "string",
    "description": "The reference of the contract affected by the transaction",
    "example": "C0103043",
    "default": "",
}

CONTRACT_ADDON_REFERENCE_SCHEMA = {
    "type": "string",
    "description": "The reference of contract of the Add-on. Use either this or lead_id when creating. ",
    "example": "C1234001-A0",
    "default": ""
}

LEAD_ID_SCHEMA = {
    "default": "",
    "description": "The ID of the lead affected by the transaction",
    "example": 123,
    "type": "integer"
}

MOBILE_UUID_SCHEMA = {
    "default": "",
    "description": "The uuid used by the mobile app",
    "example": "3fb45c94-fd4b-47a1-a65a-39075e3a9a8c",
    "oneOf": [{
        "type": "string",
    }, {
        "type": "null",
    }]
}

NULLABLE_STR = [{
    "type": "string"
}, {
    "type": "null"
}]

DEVICE_SERIAL_SCHEMA = {
    "oneOf": NULLABLE_STR,
    "description": "The serial number of the device linked to the contract",
    "example": "NPG-12345",
    "default": ""
}

NULLABLE_FLOAT = [{
    "type": "number",
    "format": "float"
}, {
    "type": "null"
}]

REQUEST_CODE_SCHEMA = {
    "oneOf": NULLABLE_STR,
    "description": "The request code needed to activate the device, if any",
    "example": "ABC12345",
    "default": None,
}

NOTES_SCHEMA = {
    "oneOf": NULLABLE_STR,
    "description": "Notes about the action",
    "example": "The contract was modified because of X",
    "default": None,
}

BOOLEAN_SCHEMA = {
    "oneOf": [
        {
            "type": "boolean"
        },
        {
            "type": "string",
            "enum": ["true", "false"]
        },
        {
            "type": "null"
        }
    ],
    "default": False,
    "example": True
}


class TransactionService:

    type = ''
    schema = {}
    permissions = []
    description = ''

    @classmethod
    def create(cls, user, uuid, time=None, **kwargs):

        with orm.db_session:
            user = user.reload() if user else None
            this_transaction = cls.get(uuid)
            if this_transaction:
                return this_transaction

            kwargs.update({'user': user})
            processed_data = cls._validate_data(**kwargs)
            if user: # not an automatic trasaction
                person = cls._get_affected_person(**processed_data)
                check_permissions_for_user(user, cls.permissions, person=person)
                check_permissions_for_user(user, ['ViewActions'], person=person)
            success = False
            offline = (time is not None)
            time = time or datetime.now()
            this_transaction = TransactionRequest(
                uuid=uuid,
                user=user,
                type=cls.type,
                time=time,
                success=success,
                client=processed_data.get('client', None),
                device=processed_data.get('this_device', None),
                offline=offline
            )
            subschema = cls.get_relevant_subschema(kwargs)
            data = {k: (kwargs[k] if k in kwargs else subschema['properties'][k].get('default')) for k in subschema['properties']}
            this_transaction.store_request_data(data)
            orm.commit()
            answer = []
            try:
                updated_data = {**data, **processed_data}
                answer = cls._process(user, offline, time, **updated_data, transaction=cls.get(uuid))
                if not isinstance(answer, list):
                    answer = [answer]
                    LogAPI.Warning(f'Answer not formatted as list: [{str(answer)}]')
                success = True
                orm.commit()
            except Error as error:
                answer = [{**{"success": False, "status": error.code, "error_message": error.get_message()}, **error.data}]
                orm.rollback()
            except Exception as exception:
                LogAPI.Fatal(exception)
                answer = [{'success': False, 'status': 'UNKNOWN_ERROR', 'error_message': str(exception)}]
                orm.rollback()

        with orm.db_session:
            this_transaction = cls.get(uuid)
            data['type'] = this_transaction.type
            AuditLogService.store_audit_log_data(user=user, data=data, object=this_transaction, action='add')
            # We do this to avoid mixing object from different transactions
            this_transaction.success = True if success and any([a['success'] for a in answer]) else False
            this_transaction.store_answer_data(answer)

            send_sms_to_client = kwargs.get('send_sms_to_client', False) in [True, 'true', 'True', 'TRUE', '1']
            if this_transaction.message_for_client and this_transaction.client and send_sms_to_client:
                MessageService.send_answer_to_person(
                    this_transaction.message_for_client,
                    this_transaction.client.person
                )
            return this_transaction

    @classmethod
    def get(cls, uuid):
        return TransactionRequest.get(uuid=uuid)

    @classmethod
    def _validate_data(cls, **kwargs):
        raise NotImplementedError

    @classmethod
    def _process(cls, user, offline, time, **kwargs):
        raise NotImplementedError
    
    @classmethod
    def _get_affected_person(cls, **kwargs):
        return (kwargs.get('client') or kwargs['lead']).person

    @staticmethod
    def _get_device(device_serial=None, contract_reference=None, user=None, create=False):
        if create and device_serial == "NON_PAYG_DEVICE":
            return NonPAYGDeviceService.create_non_payg_device()
        if device_serial:
            return Device.get(composed_serial=device_serial)
        if not contract_reference:
            return None
        contract = ContractGetterService.get_from_user_and_properties(user, reference=contract_reference)
        return contract.linked_device if contract else None

    @staticmethod
    def _get_contract(device_serial=None, contract_reference=None, user=None):
        if device_serial:
            return getattr(Device.get(composed_serial=device_serial), 'contract', None)
        return ContractGetterService.get_from_user_and_properties(user, reference=contract_reference)
    
    @staticmethod
    def _get_contract_addon(addon_reference=None, user=None):
        return AddonListService.get_from_user_and_properties(user, reference=addon_reference)

    @classmethod
    def get_relevant_subschema(cls, data):
        if 'properties' in cls.schema:
            return cls.schema
        if 'oneOf' in cls.schema:
            errors = []
            for schema in cls.schema['oneOf']:
                try:
                    validate(data, schema)
                    return schema
                except ValidationError as e:
                    errors.append(e)
            raise Exception('None of the schemas are valid: ' + str(errors))
        raise Exception

