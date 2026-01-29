from decimal import Decimal
import pytest

from werkzeug.exceptions import Forbidden
from payg_loan_system.payments.models.wallet import PaymentWallet
from payg_loan_system.contracts.models.contract_status import ContractStatus
import uuid
import json
from pony.orm import db_session, flush
from core_system.users.models.user_model import User
from payg_loan_system.transaction_requests.services.change_offer_service import ChangeOfferTransactionService
from shared.helpers.client_creator import ClientCreator
from payg_loan_system.offers.services.create_offer_service import CreateOfferService
from shared.logger.loggers import Error


class TestOfferChangeTransaction:

    id = 1
    base_offer_data  = {
        "code": "TESTCHANGEOFFER",
        "name": "TESTCHANGEOFFER",
        "type": "Loan",
        "downpayment": 10,
        "time_to_ownership_in_days": 100,
        "time_given_at_start_in_days": 10,
        "base_price_amount": 1,
        "base_price_time_in_days": 1,
        "family": 'Home',
        "base_price_time_in_days": 1,
        "automatic_unlock_code_sending": "True",
        "in_use_for_new_leads": "True",
        "can_be_approved_and_registered": "True"
    }

    @db_session
    def test_offer_change_loan_offers(self, api_client, good_api_key):

        old_offer_data = self._get_new_offer({})
        client = ClientCreator.create(api_client, good_api_key, offer_data=old_offer_data)
        contract = client.contracts.select().first()
        ClientCreator.post_payment({
            "transaction_id": "OFFER_CHANGE_PAYMENT_"+str(client.id),
            "sender_name": "OFFER_CHANGE_PAYMENT",
            "amount": '0.5',
            "memo": contract.reference
        }, api_client, good_api_key)
        new_offer_data = self._get_new_offer({
            "downpayment": 9,
            "base_price_amount": "0.5"
        })
        user = User.get(username="super_admin@test.com")
        new_offer = CreateOfferService.add_from_data_and_user(new_offer_data, user)
        assert contract.get_cumulative_amount_repaid() == 10
        assert contract.pending_amount == 0.5
        assert contract.repayments.count() == 1

        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code=new_offer.code
        )

        assert request.type == "change_offer"
        assert json.loads(request.request_data) == {
            'contract_reference': contract.reference,
            'note': None,
            'new_offer_code': new_offer.code,
            'send_sms_to_client': False
        }
        for answer in json.loads(request.answer_data):
            assert answer['success'], answer
        assert request.user == user
        assert request.success
        assert request.client == client
        assert request.device == contract.linked_device
        assert contract.offer == new_offer
        assert contract.repayments.count() == 3
        assert contract.get_cumulative_amount_repaid() == 10.5
        assert contract.pending_amount == 0

        ClientCreator.post_payment({
            "transaction_id": "OFFER_CHANGE_PAYMENT_"+str(client.id+1),
            "sender_name": "OFFER_CHANGE_PAYMENT",
            "amount": '0.4',
            "memo": contract.reference
        }, api_client, good_api_key)
        new_offer_data = self._get_new_offer({
            "downpayment": "0.8",
            "time_to_ownership_in_days": "10",
            "time_given_at_start_in_days": "0",
            "base_price_amount": 1,
            "base_price_time_in_days": 1,
        })
        new_offer = CreateOfferService.add_from_data_and_user(new_offer_data, user)

        with pytest.raises(Forbidden) as error:
            request = ChangeOfferTransactionService.create(
                user=User.get(username="view_only@test.com"),
                uuid=str(uuid.uuid1()),
                contract_reference=contract.reference,
                new_offer_code=new_offer.code
            )
        
        assert 'DoChangeOfferActions' in str(error.value)

        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code=new_offer.code
        )

        assert request.success, request.answer_data
        assert contract.pending_amount == 0
        assert contract.get_cumulative_amount_repaid() == Decimal('10.8')
        assert contract.status == ContractStatus.completed
        assert PaymentWallet.get(FullName="OFFER_CHANGE_PAYMENT").balance == Decimal('0.1')

        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code=old_offer_data['code']
        )

        assert request.success
        assert contract.pending_amount == 0
        assert contract.get_cumulative_amount_repaid() == Decimal('10.8')
        assert contract.status == ContractStatus.active

        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code=old_offer_data['code']
        )

        assert not request.success
        assert json.loads(request.answer_data)[0]['status'] == 'DEVICE_ALREADY_ON_OFFER'

        new_offer_data = self._get_new_offer({
            "downpayment": "20"
        })
        new_offer = CreateOfferService.add_from_data_and_user(new_offer_data, user)
        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code=new_offer.code
        )

        assert not request.success
        assert json.loads(request.answer_data)[0]['status'] == 'OFFER_CHANGE_FAILED_AMOUNT_PAID_BELOW_DEPOSIT'

        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code="SUPERFAKEOFFER"
        )

        assert not request.success
        assert json.loads(request.answer_data)[0]['status'] == 'OFFER_DOES_NOT_EXIST'

        new_offer_data = self._get_new_offer({
            "type": "Lump Sum",
            "base_price_amount_lump_sum": "200"
        })
        new_offer = CreateOfferService.add_from_data_and_user(new_offer_data, user)
        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code=new_offer.code
        )

        assert not request.success
        assert json.loads(request.answer_data)[0]['status'] == 'NEW_OFFER_LUMP_SUM'

        new_offer_data = self._get_new_offer({
            "type": "Time Based",
        })
        new_offer = CreateOfferService.add_from_data_and_user(new_offer_data, user)
        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code=new_offer.code
        )

        assert not request.success
        assert json.loads(request.answer_data)[0]['status'] == 'NEW_OFFER_TYPE_DIFFERENT'

        new_offer_data = self._get_new_offer({
            "in_use_for_new_leads": "False",
        })
        new_offer = CreateOfferService.add_from_data_and_user(new_offer_data, user)
        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code=new_offer.code
        )

        assert not request.success
        assert json.loads(request.answer_data)[0]['status'] == 'OFFER_DISABLED'

        new_offer_data = self._get_new_offer({
            "downpayment": "0",
            "time_to_ownership_in_days": "5"
        })
        with pytest.raises(Error) as error:
            new_offer = CreateOfferService.add_from_data_and_user(new_offer_data, user)
        assert error.value.code == 'INVALID_PRICING'

        new_offer_data = self._get_new_offer({
            "downpayment": "0",
            "time_given_at_start_in_days": "1",
            "time_to_ownership_in_days": "5"
        })
        new_offer = CreateOfferService.add_from_data_and_user(new_offer_data, user)

        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code=new_offer.code
        )

        assert not request.success
        assert json.loads(request.answer_data)[0]['status'] == 'OFFER_CHANGE_FAILED_AMOUNT_PAID_ABOVE_NEW_VALUE'

    @db_session
    def test_offer_change_time_offers(self, api_client, good_api_key):
        
        old_offer_data = self._get_new_offer({
            "type": "Time Based"
        })
        client = ClientCreator.create(api_client, good_api_key, offer_data=old_offer_data)
        contract = client.contracts.select().first()
        ClientCreator.post_payment({
            "transaction_id": "OFFER_CHANGE_PAYMENT_TIME_"+str(client.id),
            "sender_name": "OFFER_CHANGE_PAYMENT_TIME",
            "amount": '0.5',
            "memo": contract.reference
        }, api_client, good_api_key)
        new_offer_data = self._get_new_offer({
            "type": "Time Based",
            "downpayment": 9,
            "base_price_amount": "0.5"
        })
        user = User.get(username="super_admin@test.com")
        new_offer = CreateOfferService.add_from_data_and_user(new_offer_data, user)
        assert contract.get_cumulative_amount_repaid() == 10
        assert contract.pending_amount == 0.5
        assert contract.repayments.count() == 1

        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code=new_offer.code
        )

        assert request.type == "change_offer"
        assert json.loads(request.request_data) == {
            'contract_reference': contract.reference,
            'new_offer_code': new_offer.code,
            'note': None,
            'send_sms_to_client': False
        }
        for answer in json.loads(request.answer_data):
            assert answer['success'], answer
        assert request.user == user
        assert request.success
        assert request.client == client
        assert request.device == contract.linked_device
        assert contract.offer == new_offer
        assert contract.repayments.count() == 3
        assert contract.get_cumulative_amount_repaid() == 10.5
        assert contract.pending_amount == 0

        ClientCreator.post_payment({
            "transaction_id": "OFFER_CHANGE_PAYMENT_TIME_"+str(client.id+1),
            "sender_name": "OFFER_CHANGE_PAYMENT_TIME",
            "amount": '0.4',
            "memo": contract.reference
        }, api_client, good_api_key)
        new_offer_data = self._get_new_offer({
            "type": "Time Based",
            "downpayment": "0.8",
            "time_given_at_start_in_days": "0",
            "base_price_amount": 1,
            "base_price_time_in_days": 1,
        })
        new_offer = CreateOfferService.add_from_data_and_user(new_offer_data, user)

        with pytest.raises(Forbidden) as error:
            request = ChangeOfferTransactionService.create(
                user=User.get(username="view_only@test.com"),
                uuid=str(uuid.uuid1()),
                contract_reference=contract.reference,
                new_offer_code=new_offer.code
            )

        assert 'DoChangeOfferActions' in str(error.value)

        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code=new_offer.code
        )

        assert request.success, request.answer_data
        assert contract.pending_amount == Decimal('0.4')
        assert contract.get_cumulative_amount_repaid() == Decimal('10.5')
        assert contract.status == ContractStatus.active
        assert round(PaymentWallet.get(FullName="OFFER_CHANGE_PAYMENT_TIME").balance, 2) == Decimal('0')
        # the round is due to sqlite Decimal implementation limitations

        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code=old_offer_data['code']
        )

        assert request.success
        assert contract.pending_amount == Decimal('0.4')
        assert contract.get_cumulative_amount_repaid() == Decimal('10.5')
        assert contract.status == ContractStatus.active

        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code=old_offer_data['code']
        )

        assert not request.success
        assert json.loads(request.answer_data)[0]['status'] == 'DEVICE_ALREADY_ON_OFFER'

        new_offer_data = self._get_new_offer({
            "type": "Time Based",
            "downpayment": "20"
        })
        new_offer = CreateOfferService.add_from_data_and_user(new_offer_data, user)
        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code=new_offer.code
        )

        assert not request.success
        assert json.loads(request.answer_data)[0]['status'] == 'OFFER_CHANGE_FAILED_AMOUNT_PAID_BELOW_DEPOSIT'

        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code="SUPERFAKEOFFER"
        )

        assert not request.success
        assert json.loads(request.answer_data)[0]['status'] == 'OFFER_DOES_NOT_EXIST'

        new_offer_data = self._get_new_offer({
            "type": "Lump Sum",
            "base_price_amount_lump_sum": "200"
        })
        new_offer = CreateOfferService.add_from_data_and_user(new_offer_data, user)
        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code=new_offer.code
        )

        assert not request.success
        assert json.loads(request.answer_data)[0]['status'] == 'NEW_OFFER_LUMP_SUM'

        new_offer_data = self._get_new_offer({
            "type": "Loan",
        })
        new_offer = CreateOfferService.add_from_data_and_user(new_offer_data, user)
        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code=new_offer.code
        )

        assert not request.success
        assert json.loads(request.answer_data)[0]['status'] == 'NEW_OFFER_TYPE_DIFFERENT'

        new_offer_data = self._get_new_offer({
            "type": "Time Based",
            "in_use_for_new_leads": "False",
        })
        new_offer = CreateOfferService.add_from_data_and_user(new_offer_data, user)
        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code=new_offer.code
        )

        assert not request.success
        assert json.loads(request.answer_data)[0]['status'] == 'OFFER_DISABLED'

    @db_session
    def test_offer_change_usage_offers(self, api_client, good_api_key):
        
        old_offer_data = self._get_new_offer({
            "type": "Usage Based",
            "free_credit_at_start_usage_based": 10,
            "base_price_credit_in_units": 1
        })
        client = ClientCreator.create(api_client, good_api_key, offer_data=old_offer_data, device_data={
            'device_type': 'NPG'
        })
        contract = client.contracts.select().first()
        assert client is not None
        assert contract is not None
        ClientCreator.post_payment({
            "transaction_id": "OFFER_CHANGE_PAYMENT_USAGE_"+str(client.id),
            "sender_name": "OFFER_CHANGE_PAYMENT_USAGE",
            "amount": '0.5',
            "memo": contract.reference
        }, api_client, good_api_key)
        new_offer_data = self._get_new_offer({
            "type": "Usage Based",
            "downpayment": 9,
            "base_price_amount": "0.5",
            "base_price_credit_in_units": 1,
            "free_credit_at_start_usage_based": 10
        })
        user = User.get(username="super_admin@test.com")
        new_offer = CreateOfferService.add_from_data_and_user(new_offer_data, user)
        assert contract.get_cumulative_amount_repaid() == 10
        assert contract.pending_amount == 0.5
        assert contract.repayments.count() == 1

        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code=new_offer.code
        )

        assert request.type == "change_offer"
        assert json.loads(request.request_data) == {
            'contract_reference': contract.reference,
            'new_offer_code': new_offer.code,
            'note': None,
            'send_sms_to_client': False
        }
        for answer in json.loads(request.answer_data):
            assert answer['success'], answer
        assert request.user == user
        assert request.success
        assert request.client == client
        assert request.device == contract.linked_device
        assert contract.offer == new_offer
        assert contract.offer.base_price_amount == Decimal('0.5')
        assert contract.repayments.count() == 3
        assert contract.get_cumulative_amount_repaid() == 10.5
        assert contract.pending_amount == 0

        ClientCreator.post_payment({
            "transaction_id": "OFFER_CHANGE_PAYMENT_USAGE_"+str(client.id+1),
            "sender_name": "OFFER_CHANGE_PAYMENT_USAGE",
            "amount": '0.4',
            "memo": contract.reference
        }, api_client, good_api_key)
        new_offer_data = self._get_new_offer({
            "type": "Usage Based",
            "downpayment": "0.8",
            "free_credit_at_start_usage_based": 0,
            "base_price_amount": 1,
            "base_price_credit_in_units": 1,
        })
        new_offer = CreateOfferService.add_from_data_and_user(new_offer_data, user)

        with pytest.raises(Forbidden) as error:
            request = ChangeOfferTransactionService.create(
                user=User.get(username="view_only@test.com"),
                uuid=str(uuid.uuid1()),
                contract_reference=contract.reference,
                new_offer_code=new_offer.code
            )
        
        assert 'DoChangeOfferActions' in str(error.value)

        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code=new_offer.code
        )

        assert request.success
        assert contract.pending_amount == Decimal('0.4')
        assert contract.get_cumulative_amount_repaid() == Decimal('10.5')
        assert contract.status == ContractStatus.active
        assert round(PaymentWallet.get(FullName="OFFER_CHANGE_PAYMENT_USAGE").balance, 2) == Decimal('0')
        # the round is due to sqlite Decimal implementation limitations

        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code=old_offer_data['code']
        )

        assert request.success
        assert contract.pending_amount == Decimal('0.4')
        assert contract.get_cumulative_amount_repaid() == Decimal('10.5')
        assert contract.status == ContractStatus.active

        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code=old_offer_data['code']
        )

        assert not request.success
        assert json.loads(request.answer_data)[0]['status'] == 'DEVICE_ALREADY_ON_OFFER'

        new_offer_data = self._get_new_offer({
            "type": "Usage Based",
            "downpayment": "20",
            "base_price_credit_in_units": 1,
            "free_credit_at_start_usage_based": 10
        })
        new_offer = CreateOfferService.add_from_data_and_user(new_offer_data, user)
        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code=new_offer.code
        )

        assert not request.success
        assert json.loads(request.answer_data)[0]['status'] == 'OFFER_CHANGE_FAILED_AMOUNT_PAID_BELOW_DEPOSIT'

        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code="SUPERFAKEOFFER"
        )

        assert not request.success
        assert json.loads(request.answer_data)[0]['status'] == 'OFFER_DOES_NOT_EXIST'

        new_offer_data = self._get_new_offer({
            "type": "Lump Sum",
            "base_price_amount_lump_sum": "200"
        })
        new_offer = CreateOfferService.add_from_data_and_user(new_offer_data, user)
        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code=new_offer.code
        )

        assert not request.success
        assert json.loads(request.answer_data)[0]['status'] == 'NEW_OFFER_LUMP_SUM'

        new_offer_data = self._get_new_offer({})
        new_offer = CreateOfferService.add_from_data_and_user(new_offer_data, user)
        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code=new_offer.code
        )

        assert not request.success
        assert json.loads(request.answer_data)[0]['status'] == 'NEW_OFFER_TYPE_DIFFERENT'

        new_offer_data = self._get_new_offer({
            "type": "Usage Based",
            "base_price_credit_in_units": 1,
            "free_credit_at_start_usage_based": 10,
            "in_use_for_new_leads": "False",
        })
        new_offer = CreateOfferService.add_from_data_and_user(new_offer_data, user)
        request = ChangeOfferTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            new_offer_code=new_offer.code
        )

        assert not request.success
        assert json.loads(request.answer_data)[0]['status'] == 'OFFER_DISABLED'

    @classmethod
    def _get_new_offer(cls, replace):
        copy = cls.base_offer_data.copy()
        new_code = copy['code']+str(cls.id)
        cls.id += 1
        replace.update({'code': new_code, 'name': new_code})
        copy.update(replace)
        return copy
