from datetime import datetime
import dateutil
from flask_restful import Resource, request
from werkzeug.exceptions import BadRequest
from pony.orm import db_session, commit, select, exists
from core_system.person.null_person import NullPerson
from core_system.phone_numbers.model import PhoneNumbers
from core_system.users.models.user_model import User
from shared.api_helpers.server_helpers.jwt_and_schema_verification import verify
from shared.logger.loggers import LogAPI
from messages_system.models.sms_db import IncomingSMS, OutgoingSMS
from messages_system.services.sms_router import route_sms

log_api = LogAPI()

incoming_message_schema = {
    "properties": {
        "uuid": {
            "type": ["string", "null"]
        },
        "from_number": {
            "type": "string"
        },
        "to_number": {
            "type": "string"
        },
        "body": {
            "type": "string"
        },
        "sent_datetime": {
            "type": ["string", "null"]
        }
    },
    "required": ["from_number", "body", "to_number"]
}


class IncomingMessageResource(Resource):

    @verify(permissions=['AddMessages', 'AddIncomingMessages'], schema=incoming_message_schema)
    @db_session
    def post(self):

        params = request.json

        log_api.Event('Message received into PAYG API: ' + repr(params))

        if not params['body'].strip():
            return {'success': True, 'info': 'Empty SMS'}
        reception_datetime = datetime.now()
        sent_datetime = params.get('sent_datetime', None)
        if sent_datetime:
            sent_datetime = dateutil.parser.parse(sent_datetime)
        uuid = params.get('uuid', '')

        duplicate = False
        if uuid:
            duplicate = exists(sms for sms in IncomingSMS if sms.API_InternalID == uuid)

        result = 'Duplicated'
        
        if 'Web Access' in params['from_number']:
            user = User.get(id=params['from_number'].split('#')[-1])
            person = user.person if user else None
        else:
            person = select(number.person for number in PhoneNumbers if number.number == params['from_number']).first()
        
        if not duplicate:
            result = route_sms(
                params['from_number'],
                params['body'],
                reception_datetime,
                person or NullPerson()
            )
        
        IncomingSMS(
            FromNumber=params['from_number'],
            ToNumber=params['to_number'],
            Body=params['body'],
            SentTime=sent_datetime,
            ReceptionTime=reception_datetime,
            API_InternalID=uuid,
            person_id=person.id if person else None
        )
        log_api.Event('IncomingSMS created: {}'.format({repr(params)}))
        if isinstance(result, OutgoingSMS):
            result = result.Body
        return {'success': True, 'info': result}

    @verify(permissions=['AddMessages', 'AddIncomingMessages'])
    @db_session
    def put(self):
        messages_data = request.json
        if isinstance(messages_data, dict):
            messages_data = [messages_data]
        uuids = []
        updates = {}
        for item in messages_data:
            if isinstance(item, str):
                uuids.append(item)
            elif isinstance(item, dict):
                uuid = item.get('uuid')
                if uuid:
                    updates[uuid] = item
                else:
                    external_id = item.get('external_id')
                    if external_id:
                        updates[external_id] = item
        
        all_uuids = uuids + list(updates.keys())
        if all_uuids:
            messages_to_mark = select(osms for osms in OutgoingSMS if osms.API_InternalID in all_uuids or osms.external_id in all_uuids)

            for message in messages_to_mark:
                if message.API_InternalID in uuids:
                    message.IsSent = True

                updates_data = None
                if message.API_InternalID in updates:
                    updates_data = updates[message.API_InternalID]
                elif message.external_id in updates:
                    updates_data = updates[message.external_id]
                
                if updates_data:
                    message.IsSent = True

                    if 'external_id' in updates_data:
                        message.external_id = updates_data.get('external_id') or ''

                    if 'status' in updates_data:
                         message.status = updates_data.get('status') or ''
                    message.IsSent = True

        log_api.Event('Following OutgoingSMS UUIDs marked as sent: {}'.format(all_uuids))
        return {'success': True}, 200
