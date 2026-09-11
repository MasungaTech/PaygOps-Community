from decimal import Decimal

from mock import patch
from pony.orm import db_session

from core_system.core_entities import db
from payg_loan_system.payments.services.b2c_payment_service import B2CPaymentService
from shared.services.settings_service import SettingsService


class TestB2CPaymentService:

    @db_session
    @patch('payg_loan_system.payments.services.b2c_payment_service.requests.post')
    def test_add_sends_positive_amount_to_gateway_and_stores_negative_ledger_amount(self, mock_post):
        mock_post.return_value.raise_for_status.return_value = None
        user = db.User.get(username='super_admin@test.com')
        payment_data = {
            'amount': Decimal('1500.00'),
            'payment_uuid': 'B2C-TEST-POSITIVE-WIRE-AMOUNT',
            'wallet_operator': 'Mpesa-KE',
            'wallet_msisdn': '254712345678',
            'memo': 'Refund of overpayment',
            'wallet_name': 'B2C TEST WALLET',
        }

        # Paying a client out (a negative payment) is only allowed with off-taking enabled
        feature_toggles = SettingsService.get_setting('FeatureToggles')
        SettingsService.set_setting('FeatureToggles', {**feature_toggles, 'OffTaking': True})
        payment = None
        try:
            payment = B2CPaymentService.add_from_data_and_user(payment_data, user)

            # The ledger keeps the payout as a negative amount (money leaving the client wallet)...
            assert payment.Amount == Decimal('-1500.00')

            # ...but the gateway (and Safaricom B2C behind it) must receive the positive amount.
            mock_post.assert_called_once()
            payload = mock_post.call_args.kwargs['json']
            assert payload['payment_uuid'] == payment_data['payment_uuid']
            assert payload['recipient_msisdn'] == payment_data['wallet_msisdn']
            assert payload['amount'] == 1500.0
        finally:
            if payment:
                wallet = payment.PaymentWallet
                payment.delete()
                wallet.delete()
            SettingsService.set_setting('FeatureToggles', feature_toggles)
