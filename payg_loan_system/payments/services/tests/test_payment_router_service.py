from datetime import datetime
from payg_loan_system.payments.services.payment_getter_service import PaymentGetterService
from payg_loan_system.contracts.models.addon_category import AddOnCategory
from payg_loan_system.offers.models import LoanOffer
from pony import orm
import mock
from payg_loan_system.contracts.services.tests.factories import TestContractCreator
from payg_loan_system.contracts.models.reconciled_payment_type import ReconciledPaymentType
from payg_loan_system.contracts.services.contract_repayment_service import ContractRepaymentService
from payg_loan_system.offers.tests.factories import Offer, OfferType
from payg_loan_system.payments.models.wallet import PaymentWallet, PaymentWalletType
from payg_loan_system.payments.services.payment_router_service import PaymentRouterService
from payg_loan_system.contracts.services.addons.addon_offer_service import AddOnOffer, AddonOfferService, AddOnType
from payg_loan_system.contracts.services.addon_service import AddonService
from core_system.phone_numbers.services.add_phone_number_service import AddPhoneNumberService
from core_system.users.models.user_model import User
from shared.helpers.client_creator import ClientCreator
from shared.services.settings_service import SettingsService
import config

class TestPaymentRouterService:

    @orm.db_session
    def _get_or_create_offer(self):
        offer = Offer.get(name='test_offer_router')
        if not offer:
            offer = LoanOffer(
                type=OfferType.loan,
                name='test_offer_router',
                code='test_offer_router',
                family='Home',
                in_use=True,
                in_use_for_new_clients=True,
                registration_fee=1000,
                time_to_ownership_in_days=10,
                base_price_amount=1000,
                base_price_credit=1
            )
        return offer
    
    def test_available_routing_attributes_handled(self):
        payment = PaymentRouterService.handle_payment(
            reference='TESTROUTE0',
            amount=1000,
            sender_name='test_routing_attributes',
            sent_datetime=datetime.now()
        )
        for attribute in config.AVAILABLE_ROUTING_ATTRIBUTES:
            PaymentRouterService._get_routing_attribute_value(attribute, payment)
            
    @orm.db_session
    def test_available_matching_parameters_handled(self):
        for parameter in config.AVAILABLE_MATCHING_PARAMETERS:
            PaymentRouterService._get_target_from_matching_parameter_and_value(parameter, '', False, True)
            
    @orm.db_session
    def test_routes_with_wallet_name_matching_contract_reference(self, api_client, good_api_key):
        offer = self._get_or_create_offer()
        contract = TestContractCreator.create_test_contract('test_routes_with_wallet', offer=offer, npg_device=True)
        payment = PaymentRouterService.handle_payment(
            reference='TESTROUTE1',
            amount=1000,
            sender_name='test_routes_with_wallet',
            sent_datetime=datetime.now()
        )
        assert payment.reconciled_payments
        assert payment.reconciled_payments.select().first().repayment is not None
        assert payment.reconciled_payments.select().first().repayment.contract == contract
        
        response = api_client.post(config.API_PREFIX + '/payments/validate',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'TESTROUTE1',
                                         'amount': 1000,
                                         'sender_name': 'test_routes_with_wallet'})
        assert response.json['reconciled']
        
    @orm.db_session
    @mock.patch('payg_loan_system.payments.services.payment_router_service.PaymentRouterService._get_routing_rules')
    def test_routes_with_wallet_name_matching_contract_reference_not_strict(self, mock_config, api_client, good_api_key):
        mock_config.return_value = {
            '1': {'routing_attribute': 'wallet_name', 'matching_parameter': 'contract_reference', 'strict': False}
        }
        offer = self._get_or_create_offer()
        contract = TestContractCreator.create_test_contract('test_routes_with_wallet2', offer=offer, npg_device=True)
        payment = PaymentRouterService.handle_payment(
            reference='TESTROUTE7',
            amount=1000,
            sender_name='wallet2',
            sent_datetime=datetime.now()
        )
        assert payment.reconciled_payments
        assert payment.reconciled_payments.select().first().repayment is not None
        assert payment.reconciled_payments.select().first().repayment.contract == contract
        
        response = api_client.post(config.API_PREFIX + '/payments/validate',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'TESTROUTE7',
                                         'amount': 1000,
                                         'sender_name': 'wallet2'})
        assert response.json['reconciled']

    @orm.db_session
    def test_routes_with_wallet_linked_client(self, api_client, good_api_key):
        offer = self._get_or_create_offer()
        contract = TestContractCreator.create_test_contract('test_routes_with_linked_client', offer=offer, npg_device=True)
        wallet = PaymentWallet( # To do: we should not create objects directly in tests but via correspondent services
            RegistrationDate=datetime.now(),
            client=contract.client,
            Type=PaymentWalletType.mobile_money,
            FullName='TESTROUTEWALLET1',
            operator=''
        )
        payment = PaymentRouterService.handle_payment(
            reference='TESTROUTE2',
            amount=1000,
            sender_name='TESTROUTEWALLET1',
            sent_datetime=datetime.now()
        )
        assert payment.PaymentWallet == wallet
        assert payment.reconciled_payments
        assert payment.reconciled_payments.select().first().repayment is not None
        assert payment.reconciled_payments.select().first().repayment.contract == contract

        response = api_client.post(config.API_PREFIX + '/payments/validate',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'TESTROUTE2',
                                         'amount': 1000,
                                         'sender_name': 'TESTROUTEWALLET1'})
        assert response.json['reconciled']

    @orm.db_session
    def test_routes_with_wallet_phone_number(self, api_client, good_api_key):
        offer = self._get_or_create_offer()
        contract = TestContractCreator.create_test_contract('test_routes_with_wallet_phone_number', offer=offer, npg_device=True)
        AddPhoneNumberService._add_phone_number('+2341112223334', contract.client.person)
        orm.flush()
        payment = PaymentRouterService.handle_payment(
            reference='TESTROUTE3',
            amount=1000,
            sender_name='TESTROUTEWALLET2',
            sender_phone_number='+2341112223334',
            sent_datetime=datetime.now()
        )
        assert payment.reconciled_payments
        assert payment.reconciled_payments.select().first().repayment is not None
        assert payment.reconciled_payments.select().first().repayment.contract == contract

        response = api_client.post(config.API_PREFIX + '/payments/validate',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'TESTROUTE3',
                                         'amount': 1000,
                                         'sender_name': 'TESTROUTEWALLET2',
                                         'sender_phone_number': '+234111222333'})
        assert 'reconciled' in response.json, response.get_json()

    # @orm.db_session
    # @mock.patch('payg_loan_system.payments.services.payment_router_service.PaymentRouterService._get_routing_rules')
    # def test_routes_with_wallet_phone_number_not_strict(self, mock_config, api_client, good_api_key):
    #     mock_config.return_value = {
    #         '1': {'routing_attribute': 'wallet_phone_number', 'matching_parameter': 'contract_owner_phone_number', 'strict': False}
    #     }
    #     offer = self._get_or_create_offer()
    #     contract = TestContractCreator.create_test_contract('test_routes_with_wallet_phone_number2', offer=offer, npg_device=True)
    #     AddPhoneNumberService._add_phone_number('+231234567893', contract.client.person)
    #     payment = PaymentRouterService.handle_payment(
    #         reference='TESTROUTE6',
    #         amount=1000,
    #         sender_name='TESTROUTEWALLET6',
    #         sender_phone_number='567893',
    #         sent_datetime=datetime.now()
    #     )
        
    #     assert payment.reconciled_payments
    #     assert payment.reconciled_payments.select().first().repayment is not None
    #     assert payment.reconciled_payments.select().first().repayment.contract == contract

    #     response = api_client.post(config.API_PREFIX + '/payments/validate',
    #                                headers={'Authorization': 'Bearer ' + good_api_key},
    #                                json={'reference': 'TESTROUTE6',
    #                                      'amount': 1000,
    #                                      'sender_name': 'TESTROUTEWALLET6',
    #                                      'sender_phone_number': '567893'})
    #     assert response.json['reconciled']
    
    @orm.db_session
    @mock.patch('payg_loan_system.payments.services.payment_router_service.PaymentRouterService._get_routing_rules')
    def test_routes_with_memo_serial_number(self, mock_config, api_client, good_api_key):
        mock_config.return_value = {
            '1': {'routing_attribute': 'memo', 'matching_parameter': 'contract_device_serial_number'}
        }
        offer = self._get_or_create_offer()
        contract = TestContractCreator.create_test_contract('test_routes_with_memo_serial_number', offer=offer, npg_device=True)
        payment = PaymentRouterService.handle_payment(
            reference='TESTROUTE4',
            amount=1000,
            sender_name='TESTROUTEWALLET4',
            sender_phone_number='+231234567891',
            sent_datetime=datetime.now(),
            memo=str(contract.linked_device.composed_serial)
        )

        assert payment.reconciled_payments
        assert payment.reconciled_payments.select().first().repayment is not None
        assert payment.reconciled_payments.select().first().repayment.contract == contract

        response = api_client.post(config.API_PREFIX + '/payments/validate',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'TESTROUTE4',
                                         'amount': 1000,
                                         'sender_name': 'TESTROUTEWALLET4',
                                         'sender_phone_number': '+231234567891',
                                         'memo': str(contract.linked_device.composed_serial)})
        assert response.json['reconciled']

    @orm.db_session
    @mock.patch('payg_loan_system.payments.services.payment_router_service.PaymentRouterService._get_routing_rules')
    def test_routes_with_memo_serial_number_not_strict(self, mock_config, api_client, good_api_key):
        mock_config.return_value = {
            '1': {'routing_attribute': 'memo', 'matching_parameter': 'contract_device_serial_number', 'strict': False}
        }
        offer = self._get_or_create_offer()
        contract = TestContractCreator.create_test_contract('test_routes_with_memo_serial_number2', offer=offer, npg_device=True)
        payment = PaymentRouterService.handle_payment(
            reference='TESTROUTE5',
            amount=1000,
            sender_name='TESTROUTEWALLET5',
            sender_phone_number='+231234567892',
            sent_datetime=datetime.now(),
            memo=str(contract.linked_device.SerialNumber)
        )
        
        assert payment.reconciled_payments
        assert payment.reconciled_payments.select().first().repayment is not None
        assert payment.reconciled_payments.select().first().repayment.contract == contract

        response = api_client.post(config.API_PREFIX + '/payments/validate',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'TESTROUTE5',
                                         'amount': 1000,
                                         'sender_name': 'TESTROUTEWALLET5',
                                         'sender_phone_number': '+231234567892',
                                         'memo': str(contract.linked_device.SerialNumber)})
        assert response.json['reconciled']

    @orm.db_session
    @mock.patch('payg_loan_system.payments.services.payment_router_service.PaymentRouterService._get_routing_rules')
    def test_routes_with_memo_serial_number_not_strict_with_valid_fail(self, mock_config, api_client, good_api_key):
        mock_config.return_value = {
            '1': {'routing_attribute': 'memo', 'matching_parameter': 'contract_device_serial_number',
                  'strict': False, 'validity_check': '[/a-zA-Z0-9-]{4,20}'}
        }
        offer = self._get_or_create_offer()
        contract = TestContractCreator.create_test_contract('test_routes_with_memo_serial_number_not_strict_with_valid_fail', offer=offer,
                                                            npg_device=True)
        payment = PaymentRouterService.handle_payment(
            reference='TESTROUTE11',
            amount=1000,
            sender_name='TESTROUTEWALLET11',
            sender_phone_number='+231234567890',
            sent_datetime=datetime.now(),
            memo=str(contract.linked_device.composed_serial)[:2] # We take only the last 2 characters
        )

        assert not payment.reconciled_payments

        response = api_client.post(config.API_PREFIX + '/payments/validate',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'TESTROUTE11',
                                         'amount': 1000,
                                         'sender_name': 'TESTROUTEWALLET11',
                                         'sender_phone_number': '+231234567890',
                                         'memo': str(contract.linked_device.composed_serial)[:2]})
        assert not response.json['reconciled']

    @orm.db_session
    @mock.patch('payg_loan_system.payments.services.payment_router_service.PaymentRouterService._get_routing_rules')
    def test_routes_with_memo_serial_number_not_strict_with_valid_fail_2(self, mock_config, api_client, good_api_key):
        mock_config.return_value = {
            '1': {'routing_attribute': 'memo', 'matching_parameter': 'contract_device_serial_number',
                  'strict': False, 'validity_check': '[/a-zA-Z0-9-]{4,20}'}
        }
        offer = self._get_or_create_offer()
        contract = TestContractCreator.create_test_contract('test_routes_with_memo_serial_number_not_strict_with_valid_fail_2', offer=offer,
                                                            npg_device=True)
        payment = PaymentRouterService.handle_payment(
            reference='TESTROUTE13',
            amount=1000,
            sender_name='TESTROUTEWALLET13',
            sender_phone_number='+231234567890',
            sent_datetime=datetime.now(),
            memo=str(contract.linked_device.composed_serial)+'$' # We add an invalid character
        )

        assert not payment.reconciled_payments

        response = api_client.post(config.API_PREFIX + '/payments/validate',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'TESTROUTE13',
                                         'amount': 1000,
                                         'sender_name': 'TESTROUTEWALLET13',
                                         'sender_phone_number': '+231234567890',
                                         'memo': str(contract.linked_device.composed_serial)+'$'})
        assert not response.json['reconciled']

    @orm.db_session
    @mock.patch('payg_loan_system.payments.services.payment_router_service.PaymentRouterService._get_routing_rules')
    def test_routes_with_memo_serial_number_not_strict_with_valid_succeeds(self, mock_config, api_client, good_api_key):
        mock_config.return_value = {
            '1': {'routing_attribute': 'memo', 'matching_parameter': 'contract_device_serial_number',
                  'strict': False, 'validity_check': '[/a-zA-Z0-9-]{4,20}'}
        }
        offer = self._get_or_create_offer()
        contract = TestContractCreator.create_test_contract('test_routes_with_memo_serial_number_not_strict_with_valid_succeeds', offer=offer,
                                                            npg_device=True)
        payment = PaymentRouterService.handle_payment(
            reference='TESTROUTE12',
            amount=1000,
            sender_name='TESTROUTEWALLET12',
            sender_phone_number='+231234567890',
            sent_datetime=datetime.now(),
            memo=str(contract.linked_device.composed_serial)[:8]  # We take only the last 8 characters
        )

        assert payment.reconciled_payments
        assert payment.reconciled_payments.select().first().repayment is not None
        assert payment.reconciled_payments.select().first().repayment.contract == contract

        response = api_client.post(config.API_PREFIX + '/payments/validate',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'TESTROUTE12',
                                         'amount': 1000,
                                         'sender_name': 'TESTROUTEWALLET12',
                                         'sender_phone_number': '+231234567890',
                                         'memo': str(contract.linked_device.composed_serial)[:8]})
        assert response.json['reconciled']

    @orm.db_session
    def test_autolink_with_wallet_phone_number(self):
        lead = ClientCreator.create_lead()
        AddPhoneNumberService._add_phone_number('+2341112223356', lead.person)
        payment = PaymentRouterService.handle_payment(
            reference='TESTROUTE14',
            amount=10,
            sender_name='TESTROUTEWALLET14',
            sender_phone_number='+2341112223356',
            sent_datetime=datetime.now()
        )
        assert lead.deposit_paid
        assert payment.reconciled_payments
        assert payment.reconciled_payments.select().first().lead == lead
        assert not payment.orphaned
        assert not payment.orphaned_cached
        assert not payment.PaymentWallet.cached_balance_positive
        user = User.get(username="super_admin@test.com")
        assert payment not in PaymentGetterService.get_list(user, filter="orphaned")
        assert payment not in PaymentGetterService.get_list(user, filter="orphaned", cached=False)

    @orm.db_session
    def test_orphaned_when_not_routed(self, api_client, good_api_key):
        payment = PaymentRouterService.handle_payment(
            reference='TESTROUTE15',
            amount=1000,
            sender_name='TESTROUTEWALLET15',
            sender_phone_number='+234111222336',
            sent_datetime=datetime.now()
        )
        assert payment.orphaned
        assert payment.orphaned_cached
        assert payment.PaymentWallet.cached_balance_positive
        user = User.get(username="super_admin@test.com")
        assert payment in PaymentGetterService.get_list(user, filter="orphaned")
        assert payment in PaymentGetterService.get_list(user, filter="orphaned", cached=False)

        response = api_client.post(config.API_PREFIX + '/payments/validate',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'TESTROUTE15',
                                         'amount': 1000,
                                         'sender_name': 'TESTROUTEWALLET15',
                                         'sender_phone_number': '+234111222336'})
        assert not response.json['reconciled']

    @orm.db_session
    @mock.patch('payg_loan_system.payments.services.payment_router_service.PaymentRouterService._get_routing_rules')
    def test_routes_with_memo_contract_reference(self, mock_config, api_client, good_api_key):
        mock_config.return_value = {
            '1': {'routing_attribute': 'memo', 'matching_parameter': 'contract_reference'}
        }
        offer = self._get_or_create_offer()
        contract = TestContractCreator.create_test_contract('test_routes_with_memo_contract_reference', offer=offer,
                                                            npg_device=True)
        payment = PaymentRouterService.handle_payment(
            reference='TESTROUTE21',
            amount=1000,
            sender_name='TESTROUTEWALLET21',
            sender_phone_number='567893',
            sent_datetime=datetime.now(),
            memo='test_routes_with_memo_contract_reference'
        )

        assert payment.reconciled_payments
        assert payment.reconciled_payments.select().first().repayment is not None
        assert payment.reconciled_payments.select().first().repayment.contract == contract

        response = api_client.post(config.API_PREFIX + '/payments/validate',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'TESTROUTE21',
                                         'amount': 1000,
                                         'sender_name': 'TESTROUTEWALLET21',
                                         'sender_phone_number': '567893',
                                         'memo': 'test_routes_with_memo_contract_reference'})
        assert response.json['reconciled']

    # Test that it will create a reconciled payment but not a repayment if amount below minimum
    @orm.db_session
    @mock.patch('payg_loan_system.payments.services.payment_router_service.PaymentRouterService._get_routing_rules')
    def test_routes_with_memo_contract_reference_partial(self, mock_config, api_client, good_api_key):
        mock_config.return_value = {
            '1': {'routing_attribute': 'memo', 'matching_parameter': 'contract_reference'}
        }
        offer = self._get_or_create_offer()
        contract = TestContractCreator.create_test_contract('test_routes_with_memo_contract_reference_partial', offer=offer,
                                                            npg_device=True)
        payment = PaymentRouterService.handle_payment(
            reference='TESTROUTE51',
            amount=500,
            sender_name='TESTROUTEWALLET51',
            sender_phone_number='567893',
            sent_datetime=datetime.now(),
            memo='test_routes_with_memo_contract_reference_partial'
        )

        assert payment.reconciled_payments
        assert payment.reconciled_payments.select().first().repayment is None
        assert payment.reconciled_payments.select().first().contract_pending_repayment == contract
        assert payment.reconciled_payments.select().first().type == ReconciledPaymentType.repayment_pending

        response = api_client.post(config.API_PREFIX + '/payments/validate',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'TESTROUTE51',
                                         'amount': 500,
                                         'sender_name': 'TESTROUTEWALLET51',
                                         'sender_phone_number': '567893',
                                         'memo': 'test_routes_with_memo_contract_reference_partial'})
        assert response.json['reconciled']

        # Test that paying a second amount to go above the minimum links both payments
        payment_2 = PaymentRouterService.handle_payment(
            reference='TESTROUTE52',
            amount=500,
            sender_name='TESTROUTEWALLET21',
            sender_phone_number='567893',
            sent_datetime=datetime.now(),
            memo='test_routes_with_memo_contract_reference_partial'
        )

        assert payment.reconciled_payments
        assert payment.reconciled_payments.select().first().repayment is not None
        assert payment.reconciled_payments.select().first().repayment.contract == contract
        assert payment.reconciled_payments.select().first().type == ReconciledPaymentType.repayment
        assert payment_2.reconciled_payments
        assert payment_2.reconciled_payments.select().first().repayment is not None
        assert payment_2.reconciled_payments.select().first().repayment.contract == contract
        assert payment_2.reconciled_payments.select().first().type == ReconciledPaymentType.repayment

    # Same as the two steps above but with payment from two accounts
    @orm.db_session
    @mock.patch('payg_loan_system.payments.services.payment_router_service.PaymentRouterService._get_routing_rules')
    def test_routes_with_memo_contract_reference_partial_2(self, mock_config):
        mock_config.return_value = {
            '1': {'routing_attribute': 'memo', 'matching_parameter': 'contract_reference'}
        }
        offer = self._get_or_create_offer()
        contract = TestContractCreator.create_test_contract('test_routes_with_memo_contract_reference_partial_2',
                                                            offer=offer,
                                                            npg_device=True)
        payment = PaymentRouterService.handle_payment(
            reference='TESTROUTE31',
            amount=500,
            sender_name='TESTROUTEWALLET31',
            sender_phone_number='567893',
            sent_datetime=datetime.now(),
            memo='test_routes_with_memo_contract_reference_partial_2'
        )

        assert payment.reconciled_payments
        assert payment.reconciled_payments.select().first().repayment is None
        assert payment.reconciled_payments.select().first().contract_pending_repayment == contract
        assert payment.reconciled_payments.select().first().type == ReconciledPaymentType.repayment_pending

        # Test that paying a second amount to go above the minimum links both payments
        payment_2 = PaymentRouterService.handle_payment(
            reference='TESTROUTE32',
            amount=500,
            sender_name='TESTROUTEWALLET32',
            sender_phone_number='567893',
            sent_datetime=datetime.now(),
            memo='test_routes_with_memo_contract_reference_partial_2'
        )

        assert payment.reconciled_payments
        assert payment.reconciled_payments.select().first().repayment is not None
        assert payment.reconciled_payments.select().first().repayment.contract == contract
        assert payment.reconciled_payments.select().first().type == ReconciledPaymentType.repayment
        assert payment_2.reconciled_payments
        assert payment_2.reconciled_payments.select().first().repayment is not None
        assert payment_2.reconciled_payments.select().first().repayment.contract == contract
        assert payment_2.reconciled_payments.select().first().type == ReconciledPaymentType.repayment

    # Payment below minimum, then discount to complete, make sure that the payment gets unlinked
    @orm.db_session
    @mock.patch('payg_loan_system.payments.services.payment_router_service.PaymentRouterService._get_routing_rules')
    def test_routes_with_payment_below_minimum_then_discount(self, mock_config):
        mock_config.return_value = {
            '1': {'routing_attribute': 'memo', 'matching_parameter': 'contract_reference'}
        }
        offer = self._get_or_create_offer()
        contract = TestContractCreator.create_test_contract('test_routes_with_payment_below_minimum_then_discount',
                                                            offer=offer,
                                                            npg_device=True)

        amount_to_discount = contract.get_outstanding_balance_discounted()

        payment = PaymentRouterService.handle_payment(
            reference='TESTROUTE41',
            amount=500,
            sender_name='TESTROUTEWALLET41',
            sender_phone_number='567893',
            sent_datetime=datetime.now(),
            memo='test_routes_with_payment_below_minimum_then_discount'
        )

        assert payment.reconciled_payments
        assert payment.reconciled_payments.select().first().repayment is None
        assert payment.reconciled_payments.select().first().contract_pending_repayment == contract
        assert payment.reconciled_payments.select().first().type == ReconciledPaymentType.repayment_pending

        # Test that paying a second amount to go above the minimum links both payments
        ContractRepaymentService.give_amount_discount(contract, amount_to_discount)
        orm.flush()
        assert not contract.pending_amount
        assert payment.reconciled_payments.count() == 2

    @orm.db_session
    @mock.patch('payg_loan_system.payments.services.payment_router_service.PaymentRouterService._get_routing_rules')
    def test_routes_with_memo_addon_reference(self, mock_config, api_client, good_api_key):
        mock_config.return_value = {
            '1': {'routing_attribute': 'memo', 'matching_parameter': 'addon_reference'}
        }
        offer = self._get_or_create_offer()
        contract = TestContractCreator.create_test_contract('test_routes_with_memo_addon_reference',
                                                            offer=offer,
                                                            npg_device=True)

        user = User.get(username="super_admin@test.com")

        offer = AddonOfferService.create(user, "OFFER 1", "OFFERTESTROUTINGADDONS", "100",
                                         AddOnCategory.get(name="Product"), AddOnType.lump_sum,
                                         available=True)

        addon = AddonService.create(contract, offer.last_version, 1, user)

        response = api_client.post(config.API_PREFIX + '/payments/validate',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'TESTROUTEADDON',
                                         'amount': 100,
                                         'sender_name': 'TESTROUTEWALLET32',
                                         'sender_phone_number': '56789565',
                                         'memo': addon.reference})
        assert response.json['reconciled']
        
        payment = PaymentRouterService.handle_payment(
            reference='TESTROUTEADDON',
            amount=100,
            sender_name='TESTROUTEWALLET32',
            sender_phone_number='56789565',
            sent_datetime=datetime.now(),
            memo=addon.reference
        )

        assert payment.reconciled_payments
        assert payment.reconciled_payments.select().first().repayment is None
        assert payment.reconciled_payments.select().first().add_on == addon
        assert payment.reconciled_payments.select().first().type == ReconciledPaymentType.addon
        assert addon.paid

    @orm.db_session
    @mock.patch('payg_loan_system.payments.services.payment_router_service.PaymentRouterService._get_routing_rules')
    def test_routes_with_memo_addon_reference_partial(self, mock_config, api_client, good_api_key):
        mock_config.return_value = {
            '1': {'routing_attribute': 'memo', 'matching_parameter': 'addon_reference'}
        }
        offer = self._get_or_create_offer()
        contract = TestContractCreator.create_test_contract('test_routes_with_memo_addon_reference_partial',
                                                            offer=offer,
                                                            npg_device=True)

        user = User.get(username="super_admin@test.com")

        offer = AddonOfferService.create(user, "OFFER 1", "OFFERTESTROUTINGADDONS2", "100",
                                         AddOnCategory.get(name="Product"), AddOnType.lump_sum,
                                         available=True)

        addon = AddonService.create(contract, offer.last_version, 1, user)

        response = api_client.post(config.API_PREFIX + '/payments/validate',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'TESTROUTEADDONPartial',
                                         'amount': 50,
                                         'sender_name': 'TESTROUTEWALLET33',
                                         'sender_phone_number': '56789565',
                                         'memo': addon.reference})
        assert response.json['reconciled']
        
        payment = PaymentRouterService.handle_payment(
            reference='TESTROUTEADDONPartial',
            amount=50,
            sender_name='TESTROUTEWALLET33',
            sender_phone_number='56789565',
            sent_datetime=datetime.now(),
            memo=addon.reference
        )

        assert payment.reconciled_payments
        assert payment.reconciled_payments.select().first().repayment is None
        assert payment.reconciled_payments.select().first().add_on == addon
        assert payment.reconciled_payments.select().first().type == ReconciledPaymentType.addon
        assert addon.unpaid
        assert addon.already_paid == 50
        assert addon.to_pay == 50

    @orm.db_session
    @mock.patch('payg_loan_system.payments.services.payment_router_service.PaymentRouterService._get_routing_rules')
    def test_routes_with_memo_custom_id(self, mock_config, api_client, good_api_key):
        mock_config.return_value = {
            '1': {'routing_attribute': 'memo', 'matching_parameter': 'custom_id'}
        }
        offer = self._get_or_create_offer()
        contract = TestContractCreator.create_test_contract('test_routes_with_memo_custom_id',
                                                            offer=offer,
                                                            npg_device=True)
        contract.client.person.custom_id = 'TEST_CUSTOM_ID'

        response = api_client.post(config.API_PREFIX + '/payments/validate',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'TESTROUTECUSTOMID',
                                         'amount': 50,
                                         'sender_name': 'TESTROUTEWALLET34',
                                         'sender_phone_number': '56789567',
                                         'memo': 'TEST_CUSTOM_ID'})
        assert response.json['reconciled']


        response = api_client.post(config.API_PREFIX + '/payments/validate',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'TESTROUTECUSTOMID2',
                                         'amount': 50,
                                         'sender_name': 'TESTROUTEWALLET34',
                                         'sender_phone_number': '56789567',
                                         'memo': 'CUSTOM'})
        assert not response.json['reconciled']

        mock_config.return_value = {
            '1': {'routing_attribute': 'memo', 'matching_parameter': 'custom_id', 'strict': False}
        }

        response = api_client.post(config.API_PREFIX + '/payments/validate',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'TESTROUTECUSTOMID2',
                                         'amount': 50,
                                         'sender_name': 'TESTROUTEWALLET34',
                                         'sender_phone_number': '56789567',
                                         'memo': 'CUSTOM_'})
        assert response.json['reconciled']

        

    @orm.db_session
    @mock.patch('payg_loan_system.payments.services.payment_router_service.PaymentRouterService._get_routing_rules')
    def test_routes_to_addon_if_addon_unpaid(self, mock_config, api_client, good_api_key):
        mock_config.return_value = {
            '1': {'routing_attribute': 'wallet_linked_client', 'matching_parameter': 'contract_client'}
        }
        offer = self._get_or_create_offer()
        contract = TestContractCreator.create_test_contract('test_routes_to_addon_if_addon_unpaid',
                                                            offer=offer,
                                                            npg_device=True)

        user = User.get(username="super_admin@test.com")

        offer = AddonOfferService.create(user, "OFFER 1", "OFFERTESTROUTINGADDONS3", "100",
                                         AddOnCategory.get(name="Product"), AddOnType.lump_sum,
                                         available=True)

        addon = AddonService.create(contract, offer.last_version, 1, user)
        PaymentWallet(
            RegistrationDate=datetime.now(),
            client=contract.client,
            Type=PaymentWalletType.mobile_money,
            FullName='TESTROUTEWALLET34',
            operator=''
        )

        response = api_client.post(config.API_PREFIX + '/payments/validate',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'TESTROUTEADDONPRIORITY',
                                         'amount': 50,
                                         'sender_name': 'TESTROUTEWALLET34',
                                         'sender_phone_number': '567895652'})
        assert response.json['reconciled'], response.get_json()

        SettingsService.set_setting('AutomaticAddOnReconciliation', False)
        payment = PaymentRouterService.handle_payment(
            reference='TESTROUTEADDONPRIORITY',
            amount=50,
            sender_name='TESTROUTEWALLET34',
            sender_phone_number='567895652',
            sent_datetime=datetime.now()
        )

        assert payment.reconciled_payments
        assert payment.reconciled_payments.select().first().contract_pending_repayment is not None
        assert payment.reconciled_payments.select().first().contract_pending_repayment == contract
        assert payment.reconciled_payments.select().first().type == ReconciledPaymentType.repayment_pending
        assert addon.unpaid
        assert addon.already_paid == 0
        assert addon.to_pay == 100

        SettingsService.set_setting('AutomaticAddOnReconciliation', True)
        payment = PaymentRouterService.handle_payment(
            reference='TESTROUTEADDONPRIORITY2',
            amount=50,
            sender_name='TESTROUTEWALLET34',
            sender_phone_number='567895652',
            sent_datetime=datetime.now()
        )

        assert addon.unpaid
        assert addon.already_paid == 50
        assert addon.to_pay == 50

    @orm.db_session
    @mock.patch('payg_loan_system.payments.services.payment_router_service.PaymentRouterService._get_routing_rules')
    def test_routes_to_addon_if_addon_unpaid_contract(self, mock_config, api_client, good_api_key):
        mock_config.return_value = {
            '1': {'routing_attribute': 'memo', 'matching_parameter': 'contract_reference'}
        }
        offer = self._get_or_create_offer()
        contract = TestContractCreator.create_test_contract('test_routes_to_addon_if_addon_unpaid_contract',
                                                            offer=offer,
                                                            npg_device=True)

        user = User.get(username="super_admin@test.com")

        offer = AddOnOffer.get(code="OFFERTESTROUTINGADDONS3")

        addon = AddonService.create(contract, offer.last_version, 1, user)

        response = api_client.post(config.API_PREFIX + '/payments/validate',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'TESTROUTEADDONPRIORITY3',
                                         'amount': 50,
                                         'memo': contract.reference,
                                         'sender_name': 'TESTROUTEWALLET35'})
        assert response.json['reconciled']

        SettingsService.set_setting('AutomaticAddOnReconciliation', False)
        payment = PaymentRouterService.handle_payment(
            reference='TESTROUTEADDONPRIORITY3',
            amount=50,
            memo=contract.reference,
            sender_name='TESTROUTEWALLET35',
            sent_datetime=datetime.now()
        )

        assert payment.reconciled_payments.select().first() is not None
        assert payment.reconciled_payments.select().first().contract_pending_repayment is not None
        assert payment.reconciled_payments.select().first().contract_pending_repayment == contract
        assert payment.reconciled_payments.select().first().type == ReconciledPaymentType.repayment_pending
        assert addon.unpaid
        assert addon.already_paid == 0
        assert addon.to_pay == 100

        SettingsService.set_setting('AutomaticAddOnReconciliation', True)
        payment = PaymentRouterService.handle_payment(
            reference='TESTROUTEADDONPRIORITY4',
            memo=contract.reference,
            amount=50,
            sender_name='TESTROUTEWALLET35',
            sent_datetime=datetime.now()
        )

        assert addon.unpaid
        assert addon.already_paid == 50
        assert addon.to_pay == 50

    @orm.db_session
    @mock.patch('payg_loan_system.payments.services.payment_router_service.PaymentRouterService._get_routing_rules')
    def test_routes_to_addon_if_addon_unpaid_phone(self, mock_config, api_client, good_api_key):
        mock_config.return_value = {
            '1': {'routing_attribute': 'wallet_phone_number', 'matching_parameter': 'contract_owner_phone_number'}
        }
        offer = self._get_or_create_offer()
        contract = TestContractCreator.create_test_contract('test_routes_to_addon_if_addon_unpaid_phone',
                                                            offer=offer,
                                                            npg_device=True)
        AddPhoneNumberService.set_preferred_number('+2341234234234', contract.client.person)
        user = User.get(username="super_admin@test.com")
        offer = AddOnOffer.get(code="OFFERTESTROUTINGADDONS3")
        addon = AddonService.create(contract, offer.last_version, 1, user)

        PaymentWallet(
            RegistrationDate=datetime.now(),
            phone_number=contract.client.person.contactPhone,
            Type=PaymentWalletType.mobile_money,
            FullName='TESTROUTEWALLET36',
            operator=''
        )

        response = api_client.post(config.API_PREFIX + '/payments/validate',
                                   headers={'Authorization': 'Bearer ' + good_api_key},
                                   json={'reference': 'TESTROUTEADDONPRIORITY5',
                                         'sender_phone_number': '+2341234234234',
                                         'amount': 50,
                                         'sender_name': 'TESTROUTEWALLET36'})
        assert response.json['reconciled']

        SettingsService.set_setting('AutomaticAddOnReconciliation', False)
        payment = PaymentRouterService.handle_payment(
            reference='TESTROUTEADDONPRIORITY5',
            amount=50,
            sender_phone_number='+2341234234234',
            sender_name='TESTROUTEWALLET36',
            sent_datetime=datetime.now()
        )

        assert payment.reconciled_payments.select().first() is not None
        assert payment.reconciled_payments.select().first().contract_pending_repayment is not None
        assert payment.reconciled_payments.select().first().contract_pending_repayment == contract
        assert payment.reconciled_payments.select().first().type == ReconciledPaymentType.repayment_pending
        assert addon.unpaid
        assert addon.already_paid == 0
        assert addon.to_pay == 100

        SettingsService.set_setting('AutomaticAddOnReconciliation', True)
        payment = PaymentRouterService.handle_payment(
            reference='TESTROUTEADDONPRIORITY6',
            sender_phone_number='+2341234234234',
            amount=50,
            sender_name='TESTROUTEWALLET36',
            sent_datetime=datetime.now()
        )

        assert addon.unpaid
        assert addon.already_paid == 50
        assert addon.to_pay == 50

    @orm.db_session
    @mock.patch('payg_loan_system.payments.services.payment_router_service.PaymentRouterService._get_routing_rules')
    def test_routes_to_addon_if_addon_unpaid_2_addons(self, mock_config):
        mock_config.return_value = {
            '1': {'routing_attribute': 'wallet_phone_number', 'matching_parameter': 'contract_owner_phone_number'}
        }
        offer = self._get_or_create_offer()
        contract = TestContractCreator.create_test_contract('test_routes_to_addon_if_addon_unpaid_2_addons',
                                                            offer=offer,
                                                            npg_device=True)
        AddPhoneNumberService.set_preferred_number('+2341234234235', contract.client.person)
        user = User.get(username="super_admin@test.com")
        offer = AddOnOffer.get(code="OFFERTESTROUTINGADDONS3")
        addon = AddonService.create(contract, offer.last_version, 1, user)
        addon2 = AddonService.create(contract, offer.last_version, 1, user)

        PaymentWallet(
            RegistrationDate=datetime.now(),
            phone_number=contract.client.person.contactPhone,
            FullName='TESTROUTEWALLET37',
            operator=''
        )

        SettingsService.set_setting('AutomaticAddOnReconciliation', True)
        payment = PaymentRouterService.handle_payment(
            reference='TESTROUTEADDONPRIORITY7',
            sender_phone_number=contract.client.person.contactPhone.number,
            amount=200,
            sender_name='TESTROUTEWALLET36',
            sent_datetime=datetime.now()
        )

        assert addon.paid
        assert addon2.paid
