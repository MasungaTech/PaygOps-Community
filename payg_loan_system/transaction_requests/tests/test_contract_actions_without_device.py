import json
import uuid

from pony.orm import db_session, flush

from core_system.users.models.user_model import User
from payg_loan_system.contracts.models.contract_status import ContractStatus
from payg_loan_system.transaction_requests.services.cancellation_service import (
    CancelContractTransactionService,
)
from payg_loan_system.transaction_requests.services.collect_cash_service import (
    CollectCashTransactionService,
)
from payg_loan_system.transaction_requests.services.default_service import (
    DefaultTransactionService,
)
from payg_loan_system.transaction_requests.services.expected_paid_change_service import (
    ExpectedPaidChangeTransactionService,
)
from payg_loan_system.transaction_requests.services.give_delay_service import (
    GiveDelayTransactionService,
)
from payg_loan_system.transaction_requests.services.give_discount_service import (
    GiveDiscountTransactionService,
)
from payg_loan_system.transaction_requests.services.pause_contract_service import (
    PauseContractTransactionService,
)
from payg_loan_system.transaction_requests.services.resume_contract_service import (
    ResumeContractTransactionService,
)
from payg_loan_system.transaction_requests.services.undo_default_service import (
    UndoDefaultTransactionService,
)
from shared.helpers.client_creator import ClientCreator
from shared.services.settings_service import SettingsService


class TestContractActionsWithoutDevice:

    offer_id = 1

    @classmethod
    def _offer_data(cls, **replace):
        code = f'NODEVICEACTIONS{cls.offer_id}'
        cls.offer_id += 1
        data = {
            'code': code,
            'name': code,
            'type': 'Loan',
            'downpayment': 10,
            'time_to_ownership_in_days': 100,
            'time_given_at_start_in_days': 0,
            'base_price_amount': 1,
            'base_price_time_in_days': 1,
            'family': 'Home',
            'automatic_unlock_code_sending': 'True',
            'in_use_for_new_leads': 'True',
            'can_be_approved_and_registered': 'True',
            'linked_to_product': False,
        }
        data.update(replace)
        return data

    @staticmethod
    def _unlink_device(contract):
        device = contract.linked_device
        contract.linked_device = None
        if device:
            device.contract = None
        flush()
        return device

    @staticmethod
    def _assert_success(request):
        assert request.success, request.answer_data
        answers = json.loads(request.answer_data)
        assert answers
        assert all(answer['success'] for answer in answers), request.answer_data
        return answers

    @db_session
    def test_contract_actions_succeed_without_a_device(self, api_client, good_api_key):
        client = ClientCreator.create(api_client, good_api_key, offer_data=self._offer_data())
        user = User.get(username='super_admin@test.com')
        contract = client.contracts.select().first()
        self._unlink_device(contract)
        assert contract.linked_device is None

        delay = GiveDelayTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            delayed_days=1,
            note='delay without device',
        )
        self._assert_success(delay)
        assert delay.device is None

        discount = GiveDiscountTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            discounted_amount=1,
            note='discount without device',
        )
        self._assert_success(discount)
        assert discount.device is None

        cash = CollectCashTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            amount=1,
            note='cash without device',
        )
        self._assert_success(cash)
        assert cash.device is None

        expected_paid = ExpectedPaidChangeTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            adjustment_amount=1,
            note='expected paid without device',
        )
        self._assert_success(expected_paid)
        assert expected_paid.device is None

        pause = PauseContractTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            note='pause without device',
            send_sms=False,
        )
        answers = self._assert_success(pause)
        assert answers[0]['status'] == 'CONTRACT_PAUSE_SUCCESS'
        assert contract.status == ContractStatus.paused
        assert contract.linked_device is None

        resume = ResumeContractTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            note='resume without device',
        )
        answers = self._assert_success(resume)
        assert answers[0]['status'] == 'CONTRACT_RESUME_SUCCESS'
        assert contract.status == ContractStatus.active

        default = DefaultTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            note='default without device',
        )
        answers = self._assert_success(default)
        assert answers[0]['status'] == 'CONTRACT_DEFAULT_SUCCESS'
        assert contract.status == ContractStatus.defaulted
        assert default.device is None

        undo = UndoDefaultTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            note='reregister without device',
        )
        answers = self._assert_success(undo)
        assert answers[0]['success']
        assert contract.status == ContractStatus.active
        assert contract.linked_device is None

        cancel = CancelContractTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            duplicate_lead=False,
            send_sms=False,
            note='cancel without device',
        )
        answers = self._assert_success(cancel)
        assert answers[0]['status'] == 'CONTRACT_CANCELLATION_SUCCESS'
        assert contract.status == ContractStatus.cancelled

    @db_session
    def test_default_and_reregister_when_platform_has_no_devices(self, api_client, good_api_key):
        client = ClientCreator.create(
            api_client, good_api_key, offer_data=self._offer_data(linked_to_product=True)
        )
        user = User.get(username='super_admin@test.com')
        contract = client.contracts.select().first()
        self._unlink_device(contract)
        previous = SettingsService.get_setting('ContractDeviceRestrictions')
        SettingsService.set_setting('ContractDeviceRestrictions', 'no_device')
        try:
            default = DefaultTransactionService.create(
                user=user,
                uuid=str(uuid.uuid1()),
                contract_reference=contract.reference,
            )
            self._assert_success(default)
            assert contract.status == ContractStatus.defaulted

            undo = UndoDefaultTransactionService.create(
                user=user,
                uuid=str(uuid.uuid1()),
                contract_reference=contract.reference,
            )
            self._assert_success(undo)
            assert contract.status == ContractStatus.active
            assert contract.linked_device is None
        finally:
            SettingsService.set_setting('ContractDeviceRestrictions', previous)
