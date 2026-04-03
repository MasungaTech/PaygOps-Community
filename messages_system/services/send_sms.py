"""
smssync_send.py: Contains the methods to send SMS through SMSSync.
It also contain the method for SMSSync listener to get and send those messages.
"""

import hashlib
from datetime import datetime
import requests
from pony.orm import db_session, select
from core_system.phone_numbers.model import PhoneNumbers
from core_system.person.models.person_model import Person
from messages_system.models.sms_db import OutgoingSMS
from shared.helpers.clock import Clock
from shared.logger.loggers import LogAPI
from shared.api_helpers.hook_helpers.process_hook import process_hook
from shared.api_helpers.client_helpers.api_helper_object import APIHelper
from shared.services.settings_service import SettingsService
from core_system.core_entities import db
import config

Log = LogAPI()


class SMSSend:

    GATEWAY_URL = 'http://gateway:8002/api/v1/messages'

    @classmethod
    @db_session
    def SendMessage(cls, ToNumber, MessageBody, person=None, user=None):
        if not ToNumber or ToNumber == '':
            return 0

        if not MessageBody or MessageBody.replace('\n', '').replace(' ', '') == '' or not MessageBody.strip():
            return 0

        if ToNumber.isdecimal() and not str(ToNumber).startswith('+'):  
            ToNumber = '+' + str(ToNumber)

        from_number = 'solaris_crm'
        sent_datetime = Clock.now()

        uuid = cls._generate_uuid(from_number, ToNumber, MessageBody, sent_datetime)

        if person:
            person_id = person.id
        elif 'Web Access' in ToNumber:
            user = db.User.get(id=ToNumber.split('#')[-1])
            person_id = user.person.id if user else None
        else:
            person_id = select(number.person.id for number in PhoneNumbers if number.number == ToNumber).first()
            if not person_id:
                person_id = select(p.id for p in Person for number in p.phoneNumbers if number.number == ToNumber).first()

        outgoing_sms = OutgoingSMS(
            ToNumber=ToNumber,
            FromNumber=from_number,
            Body=MessageBody,
            SendingTime=datetime.now(),
            IsSent=False,
            SendingAPI='Gateway',
            API_InternalID=uuid,
            person_id=person_id,
            sending_user=user.id if user else None
        )

        if cls._is_irrelevant(ToNumber) or config.ENV_VAR == 'TEST':
            return outgoing_sms

        descriptor = cls._serialize(uuid, ToNumber, from_number, MessageBody, sent_datetime)
        try:
            cls._send(descriptor)
        except Exception as error:
            message = 'ERROR: smssync_send.py cannot connect with GATEWAY' + repr(error)
            Log.Error(message)
        finally:
            return outgoing_sms

    @classmethod
    def _serialize(cls, uuid, to_number, from_number, body, sent_datetime):
        return {
            'uuid': uuid,
            'to_number': to_number,
            'from_number': from_number,
            'body': body,
            'sent_datetime': sent_datetime
        }

    @classmethod
    def _send(cls, descriptor):
        try:
            if SettingsService.get_setting('GatewaySendingEnabled'):
                if SettingsService.get_setting('GatewaySendingAsynchronous'):
                    gateway_api = APIHelper(cls.GATEWAY_URL, '')
                    gateway_api.delayed_post('', data=descriptor)
                else:
                    requests.post(cls.GATEWAY_URL, json=descriptor, timeout=30)
        except Exception as exception:
            Log.FatalNoRequest(exception)
        process_hook('outgoing_message', descriptor)

    @classmethod
    def _is_irrelevant(cls, raw_to_number):
        is_decimal = raw_to_number.replace('+','0').isdecimal()
        return is_decimal is False

    @classmethod
    def _generate_uuid(cls, *values):
        joined_values = ''.join(str(values))
        standarized_values = str(joined_values).encode('utf-8')

        return hashlib.sha256(standarized_values).hexdigest()
