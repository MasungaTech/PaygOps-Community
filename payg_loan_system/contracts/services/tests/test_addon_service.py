from datetime import time
from decimal import Decimal

from pony.orm.core import flush
from core_system.operational_entities.services.edit_operational_entity_service import EditOperationalEntityService
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from payg_loan_system.contracts.models.addon_category import AddOnCategory
from payg_loan_system.contracts.services.addons.addon_offer_version_service import AddonOfferVersionService
from payg_loan_system.contracts.models.contract_status import ContractStatus
from payg_loan_system.offers.models import Offer, OfferType
from payg_loan_system.offers.services.create_offer_service import CreateOfferService
import pytest
from payg_loan_system.contracts.models.addons_model import AddOnLoanExtensionMode
from pony.orm import db_session
from payg_loan_system.contracts.services.addon_service import AddonService
from payg_loan_system.contracts.services.addons.addon_offer_service import AddonOfferService, AddOnType
from payg_loan_system.offers.services.edit_offer_service import EditOfferService
from shared.helpers.client_creator import ClientCreator
from core_system.users.services.user_getter_service import UserGetterService
from payg_loan_system.payments.services.reconciliation_service import ReconciliationService
from messages_system.services.message_service import MessageService


class TestAddonService:

    @db_session
    def test_create_addon(self, api_client, good_api_key):

        user = UserGetterService.get_by_username("super_admin@test.com")
        contract = ClientCreator.create(api_client, good_api_key).contracts.select().first()

        offer = AddonOfferService.create(
            user,
            "OFFER 1",
            "OFFERTOTESTADDONS",
            "15.56",
            AddOnCategory.get(name="Product"),
            AddOnType.lump_sum,
            available=True
        )

        AddonService.create(contract, offer.last_version, 1, user)
        AddonService.create(contract, offer.last_version, 1., user)
        AddonService.create(contract, offer.last_version, 1.00, user)
        AddonService.create(contract, offer.last_version, 1.000, user)

    @db_session
    def test_create_addon_offer_not_available(self, api_client, good_api_key):

        user = UserGetterService.get_by_username("super_admin@test.com")
        contract = ClientCreator.create(api_client, good_api_key).contracts.select().first()

        offer = AddonOfferService.create(
            user,
            "OFFER 2",
            "OFFERTOTESTADDONS2",
            "15.56",
            AddOnCategory.get(name="Product"),
            AddOnType.lump_sum,
            available=False
        )
        with pytest.raises(Exception) as error:
            AddonService.create(contract, offer.last_version, 1, user)
        assert error.value.code == 'OFFER_NOT_AVAILABLE_FOR_LEADS'

    @db_session
    def test_create_addon_offer_not_available_for_lead(self):

        user = UserGetterService.get_by_username("super_admin@test.com")
        lead = ClientCreator.create_lead()
        offer = AddonOfferService.create(
            user,
            "OFFER 3",
            "OFFERTOTESTADDONS3",
            "15.56",
            AddOnCategory.get(name="Product"),
            AddOnType.lump_sum,
            available=True,
            pre_sales=False
        )
        with pytest.raises(Exception) as error:
            AddonService.create(None, offer.last_version, 1, user, lead=lead)
        assert error.value.code == 'OFFER_NOT_AVAILABLE_FOR_LEADS'

    @db_session
    def test_create_loan_addons_not_available(self, api_client, good_api_key):

        user = UserGetterService.get_by_username("super_admin@test.com")
        contract = ClientCreator.create(api_client, good_api_key, offer_data={
            'code': "LOANADDONSNOTAVAILABLE",
            'allow_loan_addons': False
        }).contracts.select().first()
        offer = AddonOfferService.create(
            user,
            "OFFER 4",
            "OFFERTOTESTADDONS4",
            "15.56",
            AddOnCategory.get(name="Product"),
            AddOnType.loan,
            available=True,
            pre_sales=True
        )
        with pytest.raises(Exception) as error:
            AddonService.create(contract, offer.last_version, 1, user, loan_mode=AddOnLoanExtensionMode.amount)
        assert 'The add-on offer OFFER 4 is not available for ADDONS TEST OFFER because it does not allow loan add-ons.' in str(error.value)

    @db_session
    def test_create_addons_restricted_entities(self, api_client, good_api_key):

        user = UserGetterService.get_by_username("super_admin@test.com")
        offer = AddonOfferService.create(
            user,
            "OFFER ENTITIES",
            "OFFER_ENTITIES",
            "15.56",
            None,
            AddOnType.loan,
            available=False,
            pre_sales=False,
            need_approval=True
        )

        contract = ClientCreator.create(api_client, good_api_key).contracts.select().first()
        lead = ClientCreator.create_lead()

        with pytest.raises(Exception) as error:
            addon = AddonService.create(contract, offer.last_version, 1, user, loan_mode=AddOnLoanExtensionMode.amount)
        assert error.value.code == "OFFER_NOT_AVAILABLE_FOR_LEADS"
    
        with pytest.raises(Exception) as error:
            addon = AddonService.create(None, offer.last_version, 1, user, loan_mode=AddOnLoanExtensionMode.amount, lead=lead)
        assert error.value.code == "OFFER_NOT_AVAILABLE_FOR_LEADS"

        other_village = EditOperationalEntityService.add_from_data_and_user({
            'name': 'Other Village',
            'level': 0,
            'parent_id': lead.person.village.parent.id,
        }, user)
        flush()
        AddonOfferService.edit(user, offer, add_entities_allowed_for_contracts_ids=[other_village.id])
        assert [e.id for e in offer.entities_allowed_for_contracts] == [other_village.id]
        AddonOfferVersionService.edit(user, offer.last_version, available=True, pre_sales=True)

        addon = AddonService.create(contract, offer.last_version, 1, user, loan_mode=AddOnLoanExtensionMode.amount)
        with pytest.raises(Exception) as error:
            AddonService.approve(addon, user)
        assert str(error.value) == f"Add-on Offer OFFER ENTITIES is not available in {contract.client.person.village.name}. "
    
        AddonOfferVersionService.edit(user, offer.last_version, pre_sales=False)
        with pytest.raises(Exception) as error:
            addon = AddonService.create(None, offer.last_version, 1, user, loan_mode=AddOnLoanExtensionMode.amount, lead=lead)
        assert error.value.code == "OFFER_NOT_AVAILABLE_FOR_LEADS"

        AddonOfferService.edit(user, offer, remove_entities_allowed_for_contracts_ids=[other_village.id],
            add_entities_allowed_for_leads_ids=[other_village.id])
        AddonOfferVersionService.edit(user, offer.last_version, available=False, pre_sales=True)


        with pytest.raises(Exception) as error:
            addon = AddonService.create(contract, offer.last_version, 1, user, loan_mode=AddOnLoanExtensionMode.amount)
        assert error.value.code == f"Add-on Offer OFFER ENTITIES is not available in {lead.person.village.name}. "
    
        with pytest.raises(Exception) as error:
            addon = AddonService.create(None, offer.last_version, 1, user, loan_mode=AddOnLoanExtensionMode.amount, lead=lead)
        assert str(error.value) == f"Add-on Offer OFFER ENTITIES is not available in {lead.person.village.name}. "

        AddonOfferService.edit(user, offer, add_entities_allowed_for_contracts_ids=[contract.client.person.village.id],
            add_entities_allowed_for_leads_ids=[lead.person.village.id])
        AddonOfferVersionService.edit(user, offer.last_version, available=True, pre_sales=True)

        AddonService.create(contract, offer.last_version, 1, user, loan_mode=AddOnLoanExtensionMode.amount)    
        lead_addon = AddonService.create(None, offer.last_version, 1, user, loan_mode=AddOnLoanExtensionMode.amount, lead=lead)

        AddonOfferService.edit(user, offer, remove_entities_allowed_for_contracts_ids=[lead.person.village.id])
        AddonOfferVersionService.edit(user, offer.last_version, available=False)

        with pytest.raises(Exception) as error:
            AddonService.approve(lead_addon, user)
        assert error.value.code == "OFFER_NOT_AVAILABLE_FOR_LEADS"
        AddonOfferService.edit(user, offer, add_entities_allowed_for_contracts_ids=[other_village.id])
        AddonOfferVersionService.edit(user, offer.last_version, available=True)
        with pytest.raises(Exception) as error:
            AddonService.approve(lead_addon, user)
        assert str(error.value) == f"Add-on Offer OFFER ENTITIES is not available in {lead.person.village.name}. "
        AddonOfferService.edit(user, offer, add_entities_allowed_for_contracts_ids=[lead.person.village.id])
        AddonOfferVersionService.edit(user, offer.last_version, available=True)
        AddonService.approve(lead_addon, user)
        

    @db_session
    def test_create_addons_restricted_categories(self, api_client, good_api_key):

        user = UserGetterService.get_by_username("super_admin@test.com")
        offer = AddonOfferService.create(
            user,
            "OFFER ALLOWED",
            "OFFER_ALLOWED",
            "15.56",
            AddOnCategory.get(name="Product"),
            AddOnType.loan,
            available=True,
            need_approval=True
        )

        offer2 = AddonOfferService.create(
            user,
            "OFFER NOT ALLOWED",
            "OFFER_NOT_ALLOWED",
            "15.56",
            None,
            AddOnType.loan,
            available=True,
            need_approval=True
        )

        offer_data1 = {
            "name": "OFFER RESTRICTED",
            "code": "OFFER_RESTRICTED",
            "add_allowed_addon_offer_categories_ids": [AddOnCategory.get(name="Product").id],
        }
        contract = ClientCreator.create(api_client, good_api_key, offer_data=offer_data1).contracts.select().first()
        lead1 = ClientCreator.create_lead(offer_data1)

        offer_data2 = {
            "name": "OFFER NOT RESTRICTED",
            "code": "OFFER_NOT_RESTRICTED",
        }
        contract2 = ClientCreator.create(api_client, good_api_key, offer_data=offer_data2).contracts.select().first()
        lead2 = ClientCreator.create_lead(offer_data2)


        assert contract.offer.addon_offer_categories_allowed.select().first().name == "Product"
        assert lead1.offer.addon_offer_categories_allowed.select().first().name == "Product"
        assert not contract2.offer.addon_offer_categories_allowed
        assert not lead2.offer.addon_offer_categories_allowed

        addon = AddonService.create(contract, offer.last_version, 1, user, loan_mode=AddOnLoanExtensionMode.amount)
        AddonService.approve(addon, user)

        addon = AddonService.create(None, offer.last_version, 1, user, loan_mode=AddOnLoanExtensionMode.amount, lead=lead1)
        AddonService.approve(addon, user)

        with pytest.raises(Exception) as error:
            AddonService.create(contract, offer2.last_version, 1, user, loan_mode=AddOnLoanExtensionMode.amount)
        assert str(error.value) == "The add-on offer OFFER NOT ALLOWED is not available for the contract's offer. "
        with pytest.raises(Exception) as error:
            AddonService.create(None, offer2.last_version, 1, user, loan_mode=AddOnLoanExtensionMode.amount, lead=lead1)
        assert str(error.value) == "The add-on offer OFFER NOT ALLOWED is not available for the contract's offer. "

        addon = AddonService.create(contract2, offer.last_version, 1, user, loan_mode=AddOnLoanExtensionMode.amount)
        AddonService.approve(addon, user)

        addon = AddonService.create(None, offer.last_version, 1, user, loan_mode=AddOnLoanExtensionMode.amount, lead=lead2)
        AddonService.approve(addon, user)

        addon = AddonService.create(contract2, offer2.last_version, 1, user, loan_mode=AddOnLoanExtensionMode.amount)
        AddonService.approve(addon, user)

        addon = AddonService.create(None, offer2.last_version, 1, user, loan_mode=AddOnLoanExtensionMode.amount, lead=lead2)
        AddonService.approve(addon, user)

        EditOfferService.edit_from_data_and_user(contract.offer, {
            "add_allowed_addon_offer_categories_ids": [AddOnCategory.get(name="Service").id],
            "remove_allowed_addon_offer_categories_ids": [AddOnCategory.get(name="Product").id]
        }, user)

        EditOfferService.edit_from_data_and_user(contract2.offer, {
            "add_allowed_addon_offer_categories_ids": [AddOnCategory.get(name="Product").id],
        }, user)

        assert contract.offer.addon_offer_categories_allowed.select().first().name == "Service"
        assert contract.offer.addon_offer_categories_allowed.count() == 1
        assert contract2.offer.addon_offer_categories_allowed.select().first().name == "Product"

        with pytest.raises(Exception) as error:
            AddonService.create(contract, offer.last_version, 1, user, loan_mode=AddOnLoanExtensionMode.amount)
        assert str(error.value) == "The add-on offer OFFER ALLOWED is not available for the contract's offer. "

        with pytest.raises(Exception) as error:
            AddonService.create(None, offer.last_version, 1, user, loan_mode=AddOnLoanExtensionMode.amount, lead=lead1)
        assert str(error.value) == "The add-on offer OFFER ALLOWED is not available for the contract's offer. "

        with pytest.raises(Exception) as error:
            AddonService.create(contract, offer2.last_version, 1, user, loan_mode=AddOnLoanExtensionMode.amount)
        assert str(error.value) == "The add-on offer OFFER NOT ALLOWED is not available for the contract's offer. "

        with pytest.raises(Exception) as error:
            AddonService.create(None, offer2.last_version, 1, user, loan_mode=AddOnLoanExtensionMode.amount, lead=lead1)
        assert str(error.value) == "The add-on offer OFFER NOT ALLOWED is not available for the contract's offer. "

        addon = AddonService.create(contract2, offer.last_version, 1, user, loan_mode=AddOnLoanExtensionMode.amount)
        addon_lead = AddonService.create(None, offer.last_version, 1, user, loan_mode=AddOnLoanExtensionMode.amount, lead=lead2)

        with pytest.raises(Exception) as error:
            AddonService.create(contract2, offer2.last_version, 1, user, loan_mode=AddOnLoanExtensionMode.amount)
        assert str(error.value) == "The add-on offer OFFER NOT ALLOWED is not available for the contract's offer. "

        with pytest.raises(Exception) as error:
            AddonService.create(None, offer2.last_version, 1, user, loan_mode=AddOnLoanExtensionMode.amount, lead=lead2)
        assert str(error.value) == "The add-on offer OFFER NOT ALLOWED is not available for the contract's offer. "
        
        EditOfferService.edit_from_data_and_user(contract2.offer, {
            "add_allowed_addon_offer_categories_ids": [AddOnCategory.get(name="Service").id],
            "remove_allowed_addon_offer_categories_ids": [AddOnCategory.get(name="Product").id],
        }, user)

        with pytest.raises(Exception) as error:
            AddonService.approve(addon, user)
        assert str(error.value) == "The add-on offer OFFER ALLOWED is not available for the contract's offer. "

        with pytest.raises(Exception) as error:
            AddonService.approve(addon_lead, user)
        assert str(error.value) == "The add-on offer OFFER ALLOWED is not available for the contract's offer. "


    @db_session
    def test_create_addon_loan_extension(self, api_client, good_api_key):

        user = UserGetterService.get_by_username("super_admin@test.com")

        # 90 days to pay after the creation
        contract = ClientCreator.create(api_client, good_api_key, offer_data={
            "code": "ADDONS_TEST_EXTENSION",
            "name": "ADDONS_TEST_EXTENSION",
            "type": "Loan",
            "downpayment": 10,
            "time_to_ownership_in_days": 100,
            "time_given_at_start_in_days": 10,
            "base_price_amount": 1,
            "base_price_time_in_days": 1
        }).contracts.select().first()

        offer = AddonOfferService.create(
            user,
            "OFFEREXTENSION",
            "OFFEREXTENSION",
            "1",
            AddOnCategory.get(name="Product"),
            AddOnType.loan,
            available=True
        )

        # 45 addons of value 1 to pay over the remaining 90 days, so an extra 0.5 per day
        addon = AddonService.create(contract, offer.last_version, 45, user, loan_mode=AddOnLoanExtensionMode.amount)

        assert contract.reference_price == 1.50

        ClientCreator.post_payment({
                "transaction_id": "TestPaymentIncreased",
                "sender_name": contract.client.full_name,
                "sender_msisdn": contract.client.person.contactPhone.number,
                "amount": "1.49",
                "memo": addon.reference
            }, api_client, good_api_key)

        assert contract.repayments.count() == 1 # downpayment
        assert contract.pending_amount == Decimal('1.49') # the whole amount should still be pending as we're below the minimum

    @db_session
    def test_delivering_purchasing_addon_triggers_activation_sms(self, api_client, good_api_key, monkeypatch):
        user = UserGetterService.get_by_username("super_admin@test.com")
        contract = ClientCreator.create(api_client, good_api_key).contracts.select().first()
        offer = AddonOfferService.create(
            user,
            "PURCHASING OFFER TEST",
            "PURCHASING_OFFER_TEST",
            "30",
            AddOnCategory.get(name="Purchasing"),
            AddOnType.lump_sum,
            available=True,
            need_approval=True,
            purchasing_addon=True
        )
        addon = AddonService.create(contract, offer.last_version, 1, user, delivered=False)
        activation_answers = [{'success': True, 'status': 'CONTRACT_PAYMENT_MADE'}]
        captured = {'generator_called': 0, 'messages': 0}

        def fake_activation_generator(related_contract, repayments):
            captured['generator_called'] += 1
            assert related_contract == contract
            assert len(repayments) == 1
            return activation_answers

        def fake_send_answer(answer, person, *args):
            captured['messages'] += 1
            assert answer == activation_answers
            assert person == contract.client.person

        monkeypatch.setattr(ReconciliationService, '_generate_activation_answer_if_possible', fake_activation_generator)
        monkeypatch.setattr(MessageService, 'send_answer_to_person', fake_send_answer)

        AddonService.approve(addon, user, auto_deliver=False)
        assert addon.delivered is False
        assert addon.repayments.count() == 1

        AddonService.set_delivery_status(addon, user, delivered=True)

        assert captured['generator_called'] == 1
        assert captured['messages'] == 1

    @db_session
    def test_approving_already_delivered_purchasing_addon_triggers_activation_sms(self, api_client, good_api_key, monkeypatch):
        user = UserGetterService.get_by_username("super_admin@test.com")
        contract = ClientCreator.create(api_client, good_api_key).contracts.select().first()
        offer = AddonOfferService.create(
            user,
            "PURCHASING OFFER TEST 2",
            "PURCHASING_OFFER_TEST_2",
            "30",
            AddOnCategory.get(name="Purchasing"),
            AddOnType.lump_sum,
            available=True,
            need_approval=True,
            purchasing_addon=True
        )
        addon = AddonService.create(contract, offer.last_version, 1, user, delivered=True)
        activation_answers = [{'success': True, 'status': 'CONTRACT_PAYMENT_MADE'}]
        captured = {'generator_called': 0, 'messages': 0}

        def fake_activation_generator(related_contract, repayments):
            captured['generator_called'] += 1
            assert related_contract == contract
            assert len(repayments) == 1
            return activation_answers

        def fake_send_answer(answer, person, *args):
            captured['messages'] += 1
            assert answer == activation_answers
            assert person == contract.client.person

        monkeypatch.setattr(ReconciliationService, '_generate_activation_answer_if_possible', fake_activation_generator)
        monkeypatch.setattr(MessageService, 'send_answer_to_person', fake_send_answer)

        AddonService.approve(addon, user, auto_deliver=True)

        assert addon.delivered is True
        assert addon.repayments.count() == 1
        assert captured['generator_called'] == 1
        assert captured['messages'] == 1

    @db_session
    def test_delivering_purchasing_addon_on_lump_sum_contract_does_not_crash(
        self, api_client, good_api_key, super_admin_user, monkeypatch
    ):
        user = super_admin_user()
        lump_sum_offer = CreateOfferService.add_from_data_and_user({
            "code": "LUMP_SUM_PURCHASING_ADDON_TEST",
            "name": "Lump Sum Purchasing Addon Test",
            "type": OfferType.lump_sum,
            "base_price_amount_lump_sum": 100000,
            "family": 'Home',
            "in_use_for_new_leads": "True",
            "can_be_approved_and_registered": "True"
        }, user)
        contract = ClientCreator.create(
            api_client,
            good_api_key,
            offer_data={
                "name": lump_sum_offer.name,
                "code": lump_sum_offer.code,
                "type": lump_sum_offer.type,
                "credit_unit": lump_sum_offer.credit_unit,
                "base_price_amount": lump_sum_offer.base_price_amount,
                "base_price_credit_in_units": lump_sum_offer.base_price_credit,
                "free_credit_at_start_usage_based": lump_sum_offer.free_credit_at_start,
                "family": lump_sum_offer.family,
                "downpayment": lump_sum_offer.registration_fee
            }
        ).contracts.select().first()
        assert contract.status == ContractStatus.completed
        assert not contract.loan

        addon_offer = AddonOfferService.create(
            user,
            "PURCHASING OFFER LUMP SUM CONTRACT",
            "PURCHASING_OFFER_LUMP_SUM_CONTRACT",
            "30",
            AddOnCategory.get(name="Purchasing"),
            AddOnType.lump_sum,
            available=True,
            need_approval=True,
            purchasing_addon=True
        )
        addon = AddonService.create(contract, addon_offer.last_version, 1, user, delivered=False)
        captured_messages = []

        def fake_send_answer(answer, person, *args):
            captured_messages.append((answer, person))

        monkeypatch.setattr(MessageService, 'send_answer_to_person', fake_send_answer)

        AddonService.approve(addon, user, auto_deliver=True)

        assert addon.delivered is True
        assert addon.repayments.count() == 1
        assert captured_messages
        answer, person = captured_messages[0]
        assert person == contract.client.person
        assert answer[0]['success'] is True
        assert 'weeks_paid' not in answer[0]

