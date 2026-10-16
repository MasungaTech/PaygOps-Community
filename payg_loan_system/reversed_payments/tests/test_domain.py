import pytest

from datetime import datetime

from payg_loan_system.reversed_payments.domain import PaymentReversal
from shared.logger.loggers import Error


class TestPaymentReversal:

    def test_given_a_correct_body_may_be_deserialized(self):
        descriptor = self.some_descriptor()

        payment_reversal = PaymentReversal.deserialize(descriptor)

        expected_sent_datetime = datetime.strptime(descriptor['sent_datetime'], '%Y-%m-%dT%H:%M:%S.%fZ')
        assert payment_reversal.reference == descriptor['reference']
        assert payment_reversal.payment_reference == descriptor['payment_reference']
        assert payment_reversal.sent_datetime == expected_sent_datetime

    def test_given_a_wrong_datetime_format_raise_an_error(self):
        descriptor = self.some_descriptor()
        descriptor['sent_datetime'] = 'wrong_format'

        with pytest.raises(Error) as excinfo:
            PaymentReversal.deserialize(descriptor)

        assert 'Invalid date format' in str(excinfo)

    def test_may_has_an_amount(self):
        payment_reversal = self.generate_payment_reversal()

        payment_reversal.add_amount(1212)

        descriptor = payment_reversal.serialize()
        assert descriptor['amount'] == 1212

    def test_may_has_a_sender_name(self):
        payment_reversal = self.generate_payment_reversal()

        payment_reversal.add_sender_name('Bender')

        descriptor = payment_reversal.serialize()
        assert descriptor['sender_name'] == 'Bender'

    def test_may_has_a_sender_msisdn(self):
        payment_reversal = self.generate_payment_reversal()

        payment_reversal.add_sender_msisdn('+3466666689')

        descriptor = payment_reversal.serialize()
        assert descriptor['sender_msisdn'] == '+3466666689'

    def test_fails_when_no_proper_data(self):
        pytest.raises(TypeError, PaymentReversal)

    @staticmethod
    def generate_payment_reversal():
        return PaymentReversal(
            'some_reversal_reference',
            'some_payment_reference',
            '2018-06-14T01:58:00.000Z'
        )

    @staticmethod
    def some_descriptor():
        return {
            'reference': '123XYZ',
            'payment_reference': 'XYZ123',
            'sent_datetime': '2018-06-14T01:58:00.000Z'
        }
