import json

from pony.orm import db_session

from config import API_PREFIX


class TestPaymentRoutes:

    @staticmethod
    def test_add_payment_invalid_data(api_client, good_api_key):
        response = api_client.post(API_PREFIX + '/payments',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'something': 'isinvalid'})
        assert response.status_code == 400

    @staticmethod
    def test_add_payment_valid_data_no_msisdn(api_client, good_api_key):
        response = api_client.post(API_PREFIX + '/payments',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'A111222',
                                         'amount': 10000,
                                         'sender_name': 'John Doe',
                                         'sent_datetime': '2015-11-24T19:40:00'})
        assert response.status_code == 201

    @staticmethod
    def test_add_payment_valid_data_with_msisdn(api_client, good_api_key):
        response = api_client.post(API_PREFIX + '/payments',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'A111222',
                                         'amount': 10000,
                                         'sender_name': 'John Doe',
                                         'sent_datetime': '2015-11-24T19:40:00',
                                         'sender_msisdn': '999111222333'})
        assert response.status_code == 200

    @staticmethod
    @db_session
    def test_add_payment_invalid_value_0(api_client, good_api_key):
        response = api_client.post(API_PREFIX + '/payments',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'A1112223',
                                         'amount': 0,
                                         'sender_name': 'John Doe',
                                         'sent_datetime': '2015-11-24T19:40:00',
                                         'sender_msisdn': '999111222333'})
        assert response.status_code == 400
        assert 'The payment amount must be more than 0' in response.get_json()['error_message']

        response = api_client.post(API_PREFIX + '/payments',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'A11122235',
                                         'amount': '0',
                                         'sender_name': 'John Doe',
                                         'sent_datetime': '2015-11-24T19:40:00',
                                         'sender_msisdn': '999111222333'})
        assert response.status_code == 400
        assert 'The payment amount must be more than 0' in response.get_json()['error_message']


    @staticmethod
    @db_session
    def test_add_payment_invalid_value_negative(api_client, good_api_key):
        response = api_client.post(API_PREFIX + '/payments',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'A1112224',
                                         'amount': -1,
                                         'sender_name': 'John Doe',
                                         'sent_datetime': '2015-11-24T19:40:00',
                                         'sender_msisdn': '999111222333'})
        assert response.status_code == 400
        assert 'The payment amount must be more than 0' in response.get_json()['error_message']

        response = api_client.post(API_PREFIX + '/payments',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'A11122246',
                                         'amount': '-1',
                                         'sender_name': 'John Doe',
                                         'sent_datetime': '2015-11-24T19:40:00',
                                         'sender_msisdn': '999111222333'})
        assert response.status_code == 400
        assert 'The payment amount must be more than 0' in response.get_json()['error_message']


    @staticmethod
    def test_add_existing_payment_with_new_wallet_operator(api_client, good_api_key):
        response = api_client.post(API_PREFIX + '/payments',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'A111222',
                                         'amount': 10000,
                                         'sender_name': 'John Doe',
                                         'sent_datetime': '2015-11-24T19:40:00',
                                         'sender_msisdn': '999111222333', 
                                         'wallet_operator': 'MTN'})
        assert response.status_code == 400
    

    @staticmethod
    def test_add_new_payment_with_wallet_operator(api_client, good_api_key):
        response = api_client.post(API_PREFIX + '/payments',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'B12345',
                                         'amount': 10000,
                                         'sender_name': 'Jane Doe',
                                         'sent_datetime': '2015-11-24T19:40:00',
                                         'sender_msisdn': '999111222333', 
                                         'wallet_operator': 'MTN'})
        assert response.status_code == 201


    @staticmethod
    def test_add_payment_with_existing_reference_and_new_wallet_operator(api_client, good_api_key):
        response = api_client.post(API_PREFIX + '/payments',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'B12345',
                                         'amount': 10000,
                                         'sender_name': 'Jane Doe',
                                         'sent_datetime': '2015-11-24T19:40:00',
                                         'sender_msisdn': '999111222333', 
                                         'wallet_operator': 'MPESA'})
        assert response.status_code == 201


    @staticmethod
    def test_get_existing_payments_without_wallet_operator_parameter(api_client, good_api_key):
        response = api_client.get(API_PREFIX + '/payments/B12345',
                                   headers={'Authorization': 'Bearer ' + good_api_key})

        assert response.status_code == 400
        assert json.loads(response.data).get('error_message') == 'Multiple Payments found with the same reference, please provide a wallet operator.'


    @staticmethod
    def test_get_existing_payments_with_wallet_operator_parameter(api_client, good_api_key):
        response = api_client.get(API_PREFIX + '/payments/B12345?wallet_operator=MTN',
                                   headers={'Authorization': 'Bearer ' + good_api_key})
        assert response.status_code == 200
        payload = json.loads(response.data)
        assert payload.get('transaction_id') == 'B12345'
        assert payload.get('wallet_operator') == 'MTN'