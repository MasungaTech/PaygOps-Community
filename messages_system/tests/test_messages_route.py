from datetime import datetime
from pony import orm
from config import API_PREFIX
from messages_system.services.send_sms import SMSSend
from messages_system.models.sms_db import OutgoingSMS


class TestMessagesRoutes:

    @staticmethod
    def test_add_message_invalid_data(api_client, good_api_key):
        response = api_client.post(API_PREFIX + '/messages',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'something': 'isinvalid'})
        assert response.status_code == 400

    @staticmethod
    def test_add_message_valid_data(api_client, good_api_key):
        response = api_client.post(API_PREFIX + '/messages',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'from_number': '+999111222333',
                                         'to_number': '+999111222333',
                                         'body': 'This is a test message',
                                         'sent_datetime': '2015-11-24T19:40:00',
                                         'reception_datetime': '2015-11-24T19:40:00'})
        assert response.status_code == 200

    @staticmethod
    def test_get_web_messages(api_client, good_api_key):
        test_number = '+999111222333'
        test_body = "This is a test SMS!"
        sms_sender = SMSSend
        sms_sender.SendMessage(test_number, test_body)
        response = api_client.get(API_PREFIX + '/messages/web_answers',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   query_string={'sender_number': test_number})
        assert response.status_code == 200
        assert (test_body in str(response.data))

    @staticmethod
    @orm.db_session
    def test_mark_as_read(api_client, good_api_key):
        uuid_to_test = '111-222-333-444'
        outgoing_sms = OutgoingSMS(
            ToNumber='+999111222333',
            FromNumber='+999111222333',
            Body='This is a test',
            SendingTime=datetime.now(),
            IsSent=False,
            SendingAPI='SMSSync',
            API_InternalID=uuid_to_test
        )
        response = api_client.put(API_PREFIX + '/messages',
                                  headers={'Authorization': 'Bearer ' + good_api_key},
                                  json=[uuid_to_test])

        assert response.status_code == 200
        assert outgoing_sms.IsSent == True

    @staticmethod
    @orm.db_session
    def test_mark_status_by_external_id_after_uuid(api_client, good_api_key):
        uuid_to_test = 'payg-uuid-ext-lookup-1'
        ext_id = 'ATXid_gateway_external_1'
        outgoing_sms = OutgoingSMS(
            ToNumber='+999111222334',
            FromNumber='+999111222333',
            Body='Delivery status test',
            SendingTime=datetime.now(),
            IsSent=False,
            SendingAPI='Gateway',
            API_InternalID=uuid_to_test,
        )
        response = api_client.put(
            API_PREFIX + '/messages',
            headers={'Authorization': 'Bearer ' + good_api_key},
            json=[{'uuid': uuid_to_test, 'external_id': ext_id, 'status': 'sent'}],
        )
        assert response.status_code == 200
        assert outgoing_sms.external_id == ext_id
        assert outgoing_sms.status == 'sent'

        response = api_client.put(
            API_PREFIX + '/messages',
            headers={'Authorization': 'Bearer ' + good_api_key},
            json=[{'uuid': None, 'external_id': ext_id, 'status': 'delivered_final'}],
        )
        assert response.status_code == 200
        assert outgoing_sms.status == 'delivered_final'

    @staticmethod
    @orm.db_session
    def test_batch_status_prefers_external_id_update(api_client, good_api_key):
        uuid_to_test = 'payg-uuid-batch-1'
        ext_id = 'ATXid_batch_ext_1'
        outgoing_sms = OutgoingSMS(
            ToNumber='+999111222335',
            FromNumber='+999111222333',
            Body='Batch status test',
            SendingTime=datetime.now(),
            IsSent=False,
            SendingAPI='Gateway',
            API_InternalID=uuid_to_test,
        )
        response = api_client.put(
            API_PREFIX + '/messages',
            headers={'Authorization': 'Bearer ' + good_api_key},
            json=[
                {'uuid': uuid_to_test, 'external_id': ext_id, 'status': 'sent'},
                {'uuid': None, 'external_id': ext_id, 'status': 'delivered_final'},
            ],
        )
        assert response.status_code == 200
        assert outgoing_sms.status == 'delivered_final'

