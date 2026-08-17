from pony import orm
from payg_loan_system.payments.models.payment import Payment
from tests.factories.factories import PaymentWalletFactory
from payg_loan_system.reversed_payments.models import ReversedPayment
from datetime import datetime


class TestAcceptingPaymentReversal():

    @orm.db_session
    def teardown_method(self):
        orm.delete(reversed_payment for reversed_payment in ReversedPayment if reversed_payment.reference_code == 'my_reference')
        orm.delete(payment for payment in Payment if payment.Reference == 'payment_reference')

    @staticmethod
    def test_missing_required_fields_returns_400(api_client, good_api_key):
        route = '/api/v1/payment_reversals'
        body = {
            'reference': 'my_reference'
        }

        response = api_client.post(
            route,
            headers={'Authorization': 'Bearer ' + good_api_key},
            json=body
        )

        assert response.status_code == 400

    @staticmethod
    def test_sent_datetime_wrong_format_returns_400(api_client, good_api_key):
        route = '/api/v1/payment_reversals'
        body = {
            'reference': 'my_reference',
            'payment_reference': 'payment_reference',
            'sent_datetime': 'wrong_datetime_format'
        }

        response = api_client.post(
            route,
            headers={'Authorization': 'Bearer ' + good_api_key},
            json=body
        )

        assert response.status_code == 400

    @orm.db_session
    def test_given_all_required_fields_without_payment_related_create_reversed_payment(self, api_client, good_api_key):
        route = '/api/v1/payment_reversals'
        body = {
            "reference": "my_reference",
            "payment_reference": "payment_reference",
            "sent_datetime": "2018-06-14T01:58:00.000Z"
        }

        response = api_client.post(
            route,
            headers={'Authorization': 'Bearer ' + good_api_key},
            json=body
        )

        expected_response = {'success': True}
        expected_reversed_payment = self._get_reversed_payment_reference(body['reference'])
        assert response.json == expected_response
        assert response.status_code == 201
        assert body['reference'] in expected_reversed_payment.reference_code

    @orm.db_session
    def test_given_all_required_fields_and_sender_name_without_payment_related_create_reversed_payment(self, api_client, good_api_key):
        route = '/api/v1/payment_reversals'
        body = {
            "reference": "my_reference",
            "payment_reference": "payment_reference",
            "sent_datetime": "2018-06-14T01:58:00.000Z",
            "sender_name": "Micky Mouse"
        }

        response = api_client.post(
            route,
            headers={'Authorization': 'Bearer ' + good_api_key},
            json=body
        )

        expected_response = {'success': True}
        expected_reversed_payment = self._get_reversed_payment_reference(body['reference'])
        assert response.json == expected_response
        assert response.status_code == 201
        assert body['reference'] == expected_reversed_payment.reference_code
        assert body['sender_name'] == expected_reversed_payment.sender_name

    @orm.db_session
    def test_given_all_required_fields_and_optional_fields_without_payment_related_create_reversed_payment(self, api_client, good_api_key):
        route = '/api/v1/payment_reversals'
        body = {
            "reference": "my_reference",
            "payment_reference": "payment_reference",
            "sent_datetime": "2018-06-14T01:58:00.000Z",
            "sender_msisdn": "0012345678",
            "sender_name": "Micky Mouse",
            "amount": 1234,
        }

        response = api_client.post(
            route,
            headers={'Authorization': 'Bearer ' + good_api_key},
            json=body
        )

        expected_response = {'success': True}
        expected_reversed_payment = self._get_reversed_payment_reference(body['reference'])
        assert response.json == expected_response
        assert response.status_code == 201
        assert body['reference'] == expected_reversed_payment.reference_code
        assert body['sender_name'] == expected_reversed_payment.sender_name
        assert body['sender_msisdn'] == expected_reversed_payment.sender_msisdn
        assert body['amount'] == expected_reversed_payment.amount

    @orm.db_session
    def test_given_a_proper_body_with_a_payment_related_create_reversed_payment_and_link_it_to_its_payment(self, api_client, good_api_key):
        route = '/api/v1/payment_reversals'
        body = {
            "reference": "my_reference",
            "payment_reference": "payment_reference",
            "sent_datetime": "2018-06-14T01:58:00.000Z"
        }
        self._create_payment()

        response = api_client.post(
            route,
            headers={'Authorization': 'Bearer ' + good_api_key},
            json=body
        )

        assert response.status_code == 201
        assert self.check_reversed_payment(body['payment_reference'])
        
        response = api_client.post(
            route,
            headers={'Authorization': 'Bearer ' + good_api_key},
            json=body
        )
        
        assert response.status_code == 200
        assert self.check_reversed_payment(body['payment_reference'])

    @staticmethod
    @orm.db_session
    def _get_reversed_payment_reference(reference):
        return ReversedPayment.get(reference_code=reference)

    @staticmethod
    @orm.db_session
    def _create_payment():
        Payment(Amount=1234,
                Reference='payment_reference',
                PaymentTime=datetime.now(),
                PaymentReceptionTime=datetime.now(),
                PaymentWallet=PaymentWalletFactory())

    @staticmethod
    @orm.db_session
    def check_reversed_payment(payment_reference):
        return orm.exists(payment for payment in Payment if payment.Reference == payment_reference)
