from constants import INTEGER_OPTIONAL_OPTIONS, INTEGER_REQUIRED_OPTIONS, PHONE_PATTERN, OPTIONAL_DATETIME_OPTIONS
from datetime import datetime
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from pony.orm import *
import config
from core_system.core_entities import db as DB
from core_system.person.null_person import NullPerson

if config.TEST_MODE:
    sms_db = Database("sqlite", ':memory:', create_db=True)
else:
    sms_db = Database("postgres", user=config.PG_USER, password=config.PG_PASSWORD,
                      host=config.PG_HOST, port=config.PG_PORT, database="sms_db")


class StandardSMS:
    def __init__(self, NewTime, NewBody, NewNumber, NewType, person_id, status, external_id, sending_user):
        self.Time = NewTime
        self.Body = NewBody
        self.Number = NewNumber
        self.Type = NewType
        self.User = self._get_user()
        self.person_id = person_id
        self.person = self._get_person()
        self.status = status
        self.external_id = external_id
        self.sending_user = sending_user
        self.sending_user_object = self._get_sending_user_object()
    
    def _get_person(self):
        return DB.Person.get(id=self.person_id) if self.person_id else None
    
    # TO DO: to be removed after migration
    def _get_user(self):
        
        IsWebAccess = (self.Number.split(':')[0] == 'Web Access')
        
        if IsWebAccess:
            if len(self.Number.split(': ')) >= 2:
                FullName = self.Number.split(': ')[1]
            else:
                FullName = 'Unknown User'

            full_name_split = FullName.split(' ')
            if len(full_name_split) > 2:
                user_id = full_name_split[-1].replace('#', '')
                if user_id.isnumeric():
                    user_acting = select(U for U in DB.User if U.id == user_id).first()
                else:
                    user_acting = select(U for U in DB.User if U.person.full_name == FullName).first()
            else:
                user_acting = select(U for U in DB.User if U.person.full_name == FullName).first()
            return user_acting

        NumberExists = exists(P for P in DB.PhoneNumbers if P.number == self.Number)
        if NumberExists:
            Number = select(P for P in DB.PhoneNumbers if P.number == self.Number).first()
            person = Number.person or NullPerson()
            if person.client:
                return person.client
            lead = person.lead.select(lambda l: not l.installed).first()
            if lead:
                return lead
            return person.user   
             
    def _get_sending_user_object(self):
        return DB.User.get(id=self.sending_user) if self.sending_user else None

class IncomingSMS(sms_db.Entity):
    id = PrimaryKey(int, auto=True)
    FromNumber = Required(str, index=True)
    ToNumber = Optional(str, index=True)
    Body = Required(LongUnicode)
    SentTime = Optional(datetime)
    ReceptionTime = Required(datetime, index=True)
    ReceptionAPI = Optional(str)
    API_InternalID = Optional(str, index=True)
    Handled = Optional(bool)
    person_id = Optional(int, index=True)

    def to_standard(self):
        return StandardSMS(
            self.ReceptionTime,
            self.Body,
            self.FromNumber,
            'In',
            self.person_id,
            '',
            '',
            ''
        )


class OutgoingSMS(sms_db.Entity, ModelDefinitionMixin):
    id = PrimaryKey(int, auto=True)
    ToNumber = Required(str, index=True)
    FromNumber = Optional(str, index=True)
    Body = Required(LongUnicode)
    SendingTime = Required(datetime, index=True)
    IsSent = Required(bool)
    SentTime = Optional(datetime)
    SendingAPI = Optional(str)
    API_InternalID = Optional(str, index=True)
    person_id = Optional(int, index=True)
    external_id = Optional(str, index=True)
    status = Optional(str)
    sending_user = Optional(int)

    def to_standard(self):
        return StandardSMS(
            self.SendingTime,
            self.Body,
            self.ToNumber,
            'Out',
            self.person_id,
            self.status,
            self.external_id,
            self.sending_user
        )

    @classmethod
    def get_model_definition(cls, op, **kwargs):
        return {
            'properties': {
                "id": {
                    "type": "integer",
                    "example": 123,
                    "description": "The ID of the Outgoing SMS",
                    "value": lambda o: o.id
                },
                "uuid": {
                    "type": "string",
                    "format": "uuid",
                    "example": "abcd1234-dcba4321-09876543",
                    "description": "The uuid of the Outgoing SMS",
                    "value": lambda o: o.API_InternalID
                },
                "to_number": {
                    "type": "string",
                    "example": "+123456789",
                    "pattern": PHONE_PATTERN,
                    "description": "The phone number to which the SMS was sent",
                    "value": lambda o: o.ToNumber
                },
                "to_user_id": {
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "description": "The ID of the user corresponding to the person to whom the SMS is sent",
                    "example": 123,
                    "value": lambda o: o.to_standard().person.user.id if o.to_standard().person and o.to_standard().person.user else None
                },
                "to_client_id": {
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "description": "The ID of the client corresponding to the person to whom the SMS is sent",
                    "example": 123,
                    "value": lambda o: o.to_standard().person.client.id if o.to_standard().person and o.to_standard().person.client else None
                },
                "to_lead_id": {
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "description": "The IDs of the lead corresponding to the person to whom the SMS is sent",
                    "example": 123,
                    "value": lambda o: None
                },
                "to_leads_id": {
                    "type": "array",
                    "items": {
                        "oneOf": INTEGER_REQUIRED_OPTIONS
                    },
                    "description": "The IDs of the lead(s) corresponding to the person to whom the SMS is sent",
                    "example": [123, 456],
                    "value": lambda o: o.to_standard().person.lead.id if o.to_standard().person and o.to_standard().person.lead else None
                },
                "to_generator_id": {
                    "oneOf": INTEGER_OPTIONAL_OPTIONS,
                    "description": "The ID of the lead generator corresponding to the person to whom the SMS is sent",
                    "example": 123,
                    "value": lambda o: o.to_standard().person.leadGenerator.id if o.to_standard().person and o.to_standard().person.leadGenerator else None
                },
                "from_number": {
                    "type": "string",
                    "example": "+123456789",
                    "description": "The phone number from which the SMS was sent",
                    "value": lambda o: o.FromNumber
                },
                "body": {
                    "type": "string",
                    "example": "This is your Outgoing SMS body",
                    "description": "The text sent as SMS",
                    "value": lambda o: o.Body
                },
                "sending_time": {
                    "oneOf": OPTIONAL_DATETIME_OPTIONS,
                    "example": "2020-09-01T14:34:54",
                    "description": "The date and time at which the SMS was sent",
                    "value": lambda o: o.SendingTime
                },
                "is_sent": {
                    "type": "boolean",
                    "description": "Flag indicating if the SMS has been sent to the SMS delivery provider",
                    "example": False,
                    "deprecated": True,
                    "value": lambda o: o.IsSent
                },
                "success": {
                    "type": "boolean",
                    "description": "Flag indicating the SMS was created successfully, for retrocompatibility",
                    "example": True,
                    "deprecated": True,
                    "value": lambda o: True
                },
                "external_id":{
                    "type": "string",
                    "description": "The external id of the SMS sent",
                    "example": "A1234",
                    "value": lambda o: o.external_id
                },
                "status":{
                    "type": "string",
                    "description": "The current status of the SMS sent",
                    "example":"created",
                    "value": lambda o: o.status
                },
                "sending_user":{
                    "type": "integer",
                    "description": "The User ID to the sender of the SMS sent",
                    "example": 123,
                    "value": lambda o: o.sending_user
                }
            },
            'view_required': [],
            'view_allowed': [],
            'view_forbidden': ["to_lead_id"],
            'edit_required': [],
            'edit_allowed': [],
            'create_allowed': ["body", "to_number", "to_user_id", "to_client_id", "to_lead_id", "to_generator_id"],
            'create_required': ["body"],
        }
