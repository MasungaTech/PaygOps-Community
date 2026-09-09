import json
from payg_loan_system.contracts.models.addon_category import AddOnCategory
import pytest
from pony.orm import db_session
from shared.helpers.client_creator import ClientCreator
from shared.logger.loggers import Error
from shared.services.settings_service import SettingsService
from sales_system.leads.services.edit_lead_service import EditLeadService
from payg_loan_system.payments.models.payment import Payment
from payg_loan_system.reversed_payments.services.service import PaymentReversalService
from payg_loan_system.contracts.services.contract_repayment_service import ContractRepaymentService
from payg_loan_system.contracts.services.addon_service import AddonService
from payg_loan_system.contracts.services.addons.addon_offer_service import AddonOfferService, AddOnType
from payg_loan_system.actions.collect_cash import handle_paycash_request
from core_system.users.models.user_model import User
from core_system.users.services.user_getter_service import UserGetterService
from config import API_PREFIX


class TestReversedPaymentReversal:

    @db_session
    def test_orphaned_payment_reversal(self, api_client, good_api_key):

        ClientCreator.post_payment({
            "transaction_id": "OrphanedPaymentToReverse",
            "sender_name": "I am No One",
            "sender_msisdn": "+2314567891235",
            "amount": '10'
        }, api_client, good_api_key)
        user = User.get(username="super_admin@test.com")
        payment = Payment.get(Reference="OrphanedPaymentToReverse")

        assert not payment.reconciled_payments
        assert not payment.reversed
        assert not payment.used
        assert not payment.reversable_use
        assert payment.reversable

        PaymentReversalService.reverse_payment(payment, user)

        assert payment.reversed
        assert payment.reversed_payment.reconciled_payment.amount == payment.Amount

    @db_session
    def test_lead_and_client_payment_reversal(self, api_client, good_api_key):

        lead = ClientCreator.create_lead()
        ClientCreator.post_payment({
            "transaction_id": "HalfDownPayment"+lead.full_name,
            "sender_name": lead.full_name,
            "sender_msisdn": ClientCreator.phone,
            "amount": str(lead.offer.registration_fee/2)
        }, api_client, good_api_key)
        user = User.get(username="super_admin@test.com")

        payment = Payment.get(Reference="HalfDownPayment"+lead.full_name)

        assert payment.reconciled_payments
        assert not payment.reversed
        assert payment.used
        assert payment.reversable_use
        assert payment.reversable

        PaymentReversalService.reverse_payment(payment, user)

        assert payment.reversed
        assert payment.reversed_payment.reconciled_payment.amount == payment.Amount
        assert payment.PaymentWallet.get_balance() == 0

        ClientCreator.post_payment({
            "transaction_id": "HalfDownPayment2Steps"+lead.full_name,
            "sender_name": lead.full_name,
            "sender_msisdn": ClientCreator.phone,
            "amount": str(lead.offer.registration_fee/2)
        }, api_client, good_api_key)

        payment = Payment.get(Reference="HalfDownPayment2Steps"+lead.full_name)

        assert payment.reconciled_payments
        assert not payment.reversed
        assert payment.used
        assert payment.reversable_use
        assert payment.reversable

        EditLeadService.refund_deposit(payment.reconciled_payments.select().first().lead)
        PaymentReversalService.reverse_payment(payment, user)

        assert payment.reversed
        assert payment.reversed_payment.reconciled_payment.amount == payment.Amount
        assert payment.PaymentWallet.get_balance() == 0

        ClientCreator.register_lead(api_client, good_api_key, lead)

        payment = Payment.get(Reference="DownPayment"+lead.full_name+"0")

        assert payment.reconciled_payments
        assert not payment.reversed
        assert payment.used
        assert not payment.reversable_use
        assert not payment.reversable

        with pytest.raises(Error) as error:
            PaymentReversalService.reverse_payment(payment, user)
        assert "The payment cannot be reversed" in str(error.value)

        assert not payment.reversed
        assert not payment.reversed_payment

        ClientCreator.post_payment({
            "transaction_id": "BelowMinimumPayment"+lead.full_name,
            "sender_name": lead.full_name,
            "sender_msisdn": ClientCreator.phone,
            "amount": str(lead.offer.base_price_amount/2)
        }, api_client, good_api_key)

        payment = Payment.get(Reference="BelowMinimumPayment"+lead.full_name)

        assert payment.reconciled_payments
        assert not payment.reversed
        assert payment.used
        assert payment.reversable_use
        assert payment.reversable

        PaymentReversalService.reverse_payment(payment, user)

        assert payment.reversed
        assert payment.reversed_payment.reconciled_payment.amount == payment.Amount
        assert payment.PaymentWallet.get_balance() == 0

        ClientCreator.post_payment({
            "transaction_id": "RePayment"+lead.full_name,
            "sender_name": lead.full_name,
            "sender_msisdn": ClientCreator.phone,
            "amount": str(lead.offer.base_price_amount)
        }, api_client, good_api_key)

        payment = Payment.get(Reference="RePayment"+lead.full_name)

        assert payment.reconciled_payments
        assert not payment.reversed
        assert payment.used
        assert payment.reversable_use
        assert payment.reversable

        PaymentReversalService.reverse_payment(payment, user)

        assert payment.reversed
        assert payment.reversed_payment.reconciled_payment.amount == payment.Amount
        assert payment.PaymentWallet.get_balance() == 0

        ClientCreator.post_payment({
            "transaction_id": "RepaymentFromBalance"+lead.full_name,
            "sender_name": 'Different Name',
            "sender_msisdn": '',
            "amount": str(lead.offer.base_price_amount*2)
        }, api_client, good_api_key)

        payment = Payment.get(Reference="RepaymentFromBalance"+lead.full_name)

        assert not payment.reconciled_payments
        assert not payment.reversed
        assert not payment.used
        assert not payment.reversable_use
        assert payment.reversable

        ContractRepaymentService.repay_and_reconcile(
            lead.contract,
            account=payment.PaymentWallet,
            amount=lead.offer.base_price_amount
        )

        assert not payment.reconciled_payments
        assert not payment.reversed
        assert payment.used
        assert not payment.reversable_use
        assert not payment.reversable

        with pytest.raises(Error) as error:
            PaymentReversalService.reverse_payment(payment, user)
        assert "The payment cannot be reversed" in str(error.value)

        assert not payment.reversed
        assert not payment.reversed_payment

        offer = AddonOfferService.create(
            user,
            "OFFER 1",
            "ADDONOFFERREVERSAL",
            "15.56",
            AddOnCategory.get(name="Product"),
            AddOnType.lump_sum,
            available=True)
        user = UserGetterService.get_by_username("super_admin@test.com")
        addon = AddonService.create(lead.contract, offer.last_version, 1, user)
        AddonService.pay_with_cash(addon, user)

        payment = addon.reconciled_payments.select().first().linked_payment

        assert payment.reconciled_payments
        assert not payment.reversed
        assert payment.used
        assert not payment.reversable_use
        assert not payment.reversable

        with pytest.raises(Error) as error:
            PaymentReversalService.reverse_payment(payment, user)
        assert "The payment cannot be reversed" in str(error.value)

        assert not payment.reversed
        assert not payment.reversed_payment

        assert not payment.back_payment.reconciled_payments
        assert not payment.back_payment.reversed
        assert not payment.back_payment.used
        assert not payment.back_payment.reversable_use
        assert not payment.back_payment.reversable

        with pytest.raises(Error) as error:
            PaymentReversalService.reverse_payment(payment.back_payment)
        assert "The payment cannot be reversed" in str(error.value)

        assert not payment.back_payment.reversed
        assert not payment.back_payment.reversed_payment

        answer = handle_paycash_request(
            user,
            lead.offer.base_price_amount,
            lead.contract.linked_device
        )

        payment = Payment.get(Reference=answer[0]['transaction_id'])

        assert not payment.back_payment.reconciled_payments
        assert not payment.back_payment.reversed
        assert not payment.back_payment.used
        assert not payment.back_payment.reversable_use
        assert not payment.back_payment.reversable

        with pytest.raises(Error) as error:
            PaymentReversalService.reverse_payment(payment.back_payment, user)
        assert "The payment cannot be reversed" in str(error.value)

        assert not payment.back_payment.reversed
        assert not payment.back_payment.reversed_payment

        assert payment.reconciled_payments
        assert not payment.reversed
        assert payment.used
        assert payment.reversable_use
        assert payment.reversable
        cash_balance = payment.back_payment.PaymentWallet.get_balance()

        PaymentReversalService.reverse_payment(payment, user)

        assert payment.reversed
        assert payment.reversed_payment.reconciled_payment.amount == payment.Amount
        assert payment.PaymentWallet.get_balance() == 0
        assert payment.back_payment.PaymentWallet.get_balance() == cash_balance-lead.offer.base_price_amount

        ClientCreator.post_payment({
            "transaction_id": "RePaymentToReverse2Steps"+lead.full_name,
            "sender_name": lead.full_name,
            "sender_msisdn": ClientCreator.phone,
            "amount": str(lead.offer.base_price_amount)
        }, api_client, good_api_key)

        payment = Payment.get(Reference="RePaymentToReverse2Steps"+lead.full_name)

        assert payment.reconciled_payments
        assert not payment.reversed
        assert payment.used
        assert payment.reversable_use
        assert payment.reversable

        ContractRepaymentService.reverse_repayment(payment.reconciled_payments.select().first().repayment,
                                                   user)
        PaymentReversalService.reverse_payment(payment, user)

        assert payment.reversed
        assert payment.reversed_payment.reconciled_payment.amount == payment.Amount
        assert payment.PaymentWallet.get_balance() == 0

    @db_session
    def test_api_payment_reversal(self, api_client, admin_api_key):

        ClientCreator.post_payment({
            "transaction_id": "PaymentToReverseByAPI",
            "sender_name": "I am No One",
            "sender_msisdn": ClientCreator.phone,
            "amount": '10'
        }, api_client, admin_api_key)

        payment = Payment.get(Reference="PaymentToReverseByAPI")

        assert payment.reconciled_payments
        assert not payment.reversed
        assert payment.used
        assert payment.reversable_use
        assert payment.reversable

        SettingsService.set_setting('AutomaticPaymentReversal', False)
        SettingsService.set_setting('AutomaticRepaymentReversal', False)
        resp = api_client.post(
            API_PREFIX + '/payment_reversals',
            json={
                'payment_reference': "PaymentToReverseByAPI",
                'reference': 'ReversalRequestByAPI'
            },
            headers={'Authorization': 'Bearer ' + admin_api_key}
        )

        assert not payment.reversed
        assert payment.reversed_payment.reference_code == 'ReversalRequestByAPI'

        ClientCreator.post_payment({
            "transaction_id": "PaymentToReverseByAPI2",
            "sender_name": "I am No One",
            "sender_msisdn": ClientCreator.phone,
            "amount": '10'
        }, api_client, admin_api_key)

        payment = Payment.get(Reference="PaymentToReverseByAPI2")

        assert payment.reconciled_payments
        assert not payment.reversed
        assert payment.used
        assert payment.reversable_use
        assert payment.reversable

        SettingsService.set_setting('AutomaticPaymentReversal', True)
        SettingsService.set_setting('AutomaticRepaymentReversal', False)
        resp = api_client.post(
            API_PREFIX + '/payment_reversals',
            json={
                'payment_reference': "PaymentToReverseByAPI2",
                'reference': 'ReversalRequestByAPI2'
            },
            headers={'Authorization': 'Bearer ' + admin_api_key}
        )

        assert json.loads(next(resp.response))['success']
        assert payment.reversed
        
        ClientCreator.post_payment({
            "transaction_id": "PaymentToReverseByAPI3",
            "sender_name": "I am No One",
            "sender_msisdn": ClientCreator.phone,
            "amount": '10'
        }, api_client, admin_api_key)

        payment = Payment.get(Reference="PaymentToReverseByAPI3")

        assert payment.reconciled_payments
        assert not payment.reversed
        assert payment.used
        assert payment.reversable_use
        assert payment.reversable

        SettingsService.set_setting('AutomaticPaymentReversal', True)
        SettingsService.set_setting('AutomaticRepaymentReversal', True)
        resp = api_client.post(
            API_PREFIX + '/payment_reversals',
            json={
                'payment_reference': "PaymentToReverseByAPI3",
                'reference': 'ReversalRequestByAPI3'
            },
            headers={'Authorization': 'Bearer ' + admin_api_key}
        )

        resp_data = json.loads(next(resp.response))
        assert resp_data['success'], resp_data
        assert payment.reversed
        assert payment.reversed_payment.reconciled_payment.amount == payment.Amount
        assert payment.PaymentWallet.get_balance() == 0
