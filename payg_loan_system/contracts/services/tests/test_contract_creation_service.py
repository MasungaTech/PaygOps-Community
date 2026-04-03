from decimal import Decimal

import pytest
from payg_loan_system.contracts.models.repayment_discount_types import ContractRepaymentDiscountTypes
from mock import patch
from flask_login import current_user
from pony.orm import db_session, flush
from payg_loan_system.contracts.services.contract_creation_service import ContractCreationService
from payg_loan_system.contracts.services.tests.factories import ContractFactory, DeviceFactory
from payg_loan_system.offers.tests.factories import TimeOfferFactory
from sales_system.leads.tests.factories import LeadFactory
from shared.helpers.client_creator import ClientCreator
from shared.logger.loggers import Error


class TestContractCreationService:

    @staticmethod
    def _check_error(lead, device, user, error_name, data=None):
        try:
            ContractCreationService.create_from_lead_and_device(lead=lead, device=device, acting_user=user)
        except Error as error:
            assert error.args[0] == error_name
            if data:
                assert error.data == data
        else:
            raise Exception(f'Error {error} not raised')

    def test_lead_not_approved(self):
        lead = LeadFactory.stub()
        lead.decision = False
        device = DeviceFactory.stub(contracts=None)

        self._check_error(lead, device, current_user, 'LEAD_NOT_APPROVED')

    # We currently prevent the creation of multiple contracts on one client
    class TestClientSmsHandler:
        @pytest.fixture(autouse=True)
        @db_session
        def test_lead_already_has_client(self, api_client, good_api_key):
            lead = LeadFactory.stub()
            lead.installed = True
            lead.person.client = ClientCreator.create(api_client, good_api_key)
            device = DeviceFactory.stub(contract=None)

            self._check_error(lead, device, current_user, 'LEAD_ALREADY_REGISTERED', {'client_id': lead.person.client.id})

    def test_lead_offer_not_exists(self):
        lead = LeadFactory.stub()
        lead.offer = None
        device = DeviceFactory.stub(contract=None)
        lead.deposit_paid = True
        
        self._check_error(lead, device, current_user, 'OFFER_DOES_NOT_EXIST')

    def test_lead_offer_disabled(self):
        lead = LeadFactory.stub()
        lead.offer = TimeOfferFactory.stub(in_use=False)
        device = DeviceFactory.stub(contract=None)
        lead.deposit_paid = True

        self._check_error(lead, device, current_user, 'OFFER_DISABLED')

    @patch('payg_loan_system.contracts.services.contract_creation_service.SettingsService.get_setting')
    def test_lead_device_incompatible_with_offer(self, mock_get_setting):
        mock_get_setting.return_value = 'require_device'
        lead = LeadFactory.stub()
        lead.offer = TimeOfferFactory.stub(device_type='XXX')
        lead.deposit_paid = True
        device = DeviceFactory.stub(contract=None)

        self._check_error(lead, device, current_user, 'DEVICE_NOT_ALLOWED_ON_OFFER')

    @patch('payg_loan_system.contracts.services.contract_creation_service.SettingsService.get_setting')
    def test_lead_device_already_used(self, mock_get_setting):
        mock_get_setting.return_value = 'require_device'
        lead = LeadFactory.stub()
        lead.offer = TimeOfferFactory.stub()
        lead.deposit_paid = True
        device = DeviceFactory.stub(contract=None)
        device.contract = ContractFactory.stub()

        self._check_error(lead, device, current_user, 'DEVICE_ALREADY_REGISTERED', {'device_owner_id': device.contract.client.id})

    def test_lead_no_deposit_payment(self):
        lead = LeadFactory.stub()
        lead.offer = TimeOfferFactory.stub()
        device = DeviceFactory.stub(contract=None)

        with patch.object(lead, 'deposit_paid', False, create=True):
            self._check_error(lead, device, current_user, 'LEAD_INITIAL_PAYMENT_NOT_PAID')

    @db_session
    def test_initial_repayment_creation_for_lead_with_pending_reconciled_payments(self, api_client, good_api_key):

        lead = ClientCreator.create_lead()
        ClientCreator.register_lead(api_client, good_api_key, lead, extra_paid=Decimal('50'))
        flush()
        assert lead.contract.repayments.select()[:][-1].discount_type != ContractRepaymentDiscountTypes.downpayment
        assert lead.contract.repayments.select()[:][-1].amount == 50

    @db_session
    def test_initial_repayment_creation_for_lead_with_pending_reconciled_payments_below_minimum(self, api_client, good_api_key):
        lead = ClientCreator.create_lead()
        ClientCreator.register_lead(api_client, good_api_key, lead, extra_paid=Decimal('0.5'))
        assert lead.contract.repayments.select()[:][-1].discount_type == ContractRepaymentDiscountTypes.downpayment
