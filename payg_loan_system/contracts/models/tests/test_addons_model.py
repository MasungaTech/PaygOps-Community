from payg_loan_system.contracts.models.addon_category import AddOnCategory
from payg_loan_system.contracts.models.contract_event_model import ContractEventType
from pony.orm import db_session, flush
from payg_loan_system.contracts.services.addon_service import AddonService
from payg_loan_system.contracts.services.addons.addon_offer_service import (
    AddonOfferService, AddOnType, AddOnLoanExtensionMode)
from core_system.users.services.user_getter_service import UserGetterService
from shared.helpers.client_creator import ClientCreator
import pytest


class TestAddonModel:

    @classmethod
    @pytest.fixture(autouse=True)
    def setup_class(cls, api_client, good_api_key):
        cls.api_client = api_client
        cls.good_api_key = good_api_key

    @db_session
    def test_addon_model_extension_contract_duration(self, api_client, good_api_key):

        user = UserGetterService.get_by_username("super_admin@test.com")
        contract = ClientCreator.create(api_client, good_api_key).contracts.select().first()
        offer = AddonOfferService.create(
            user,
            "OFFER TEST EXTENSION DAYS",
            "OFFEREXTDAYS1",
            "10",
            AddOnCategory.get(name="Product"),
            AddOnType.loan,
            available=True,
            loan_mode=AddOnLoanExtensionMode.duration,
            downpayment="3"
        )
        addon = AddonService.create(contract, offer.last_version, 1, user)
        assert addon.extension_days == 10
        assert addon.repayment_increase == 0
        assert addon.principal == 7
        assert addon.downpayment == 3

    @db_session
    def test_addon_model_extension_lead_duration(self):

        user = UserGetterService.get_by_username("super_admin@test.com")
        lead = ClientCreator.create_lead()
        offer = AddonOfferService.create(
            user,
            "OFFER TEST EXTENSION DAYS2",
            "OFFEREXTDAYS2",
            "10",
            AddOnCategory.get(name="Product"),
            AddOnType.loan,
            available=True,
            loan_mode=AddOnLoanExtensionMode.duration,
            downpayment="3"
        )
        addon = AddonService.create(None, offer.last_version, 1, user, lead=lead)
        assert addon.extension_days == 7
        assert addon.repayment_increase == 0
        assert addon.principal == 7
        assert addon.downpayment == 3
        flush()
        assert offer.last_version.lead_addons.count() == 1

    @db_session
    def test_addon_model_extension_contract_repayment(self, api_client, good_api_key):

        user = UserGetterService.get_by_username("super_admin@test.com")
        offer = AddonOfferService.create(
            user,
            "OFFER TEST EXTENSION AMOUNT",
            "OFFEREXTAMOUNT",
            10,
            AddOnCategory.get(name="Product"),
            AddOnType.loan,
            available=True,
            loan_mode=AddOnLoanExtensionMode.amount,
            downpayment=3
        )
        contract = ClientCreator.create(api_client, good_api_key).contracts.select().first()
        addon = AddonService.create(contract, offer.last_version, 1, user)
        assert addon.extension_days == 0
        assert addon.repayment_increase == round(offer.last_version.price/contract.offer.time_to_ownership_in_days, 2)
        assert addon.principal == 7
        assert addon.downpayment == 3

    @db_session
    def test_addon_model_extension_lead_repayment(self, api_client, good_api_key):

        user = UserGetterService.get_by_username("super_admin@test.com")
        offer = AddonOfferService.create(
            user,
            "OFFER TEST EXTENSION AMOUNT 2",
            "OFFEREXTAMOUNT2",
            10,
            AddOnCategory.get(name="Product"),
            AddOnType.loan,
            available=True,
            loan_mode=AddOnLoanExtensionMode.amount,
            downpayment=3
        )
        lead = ClientCreator.create_lead()
        addon = AddonService.create(None, offer.last_version, 1, user, lead=lead)
        assert addon.extension_days == 0
        assert addon.repayment_increase == round((offer.last_version.price-addon.downpayment)/lead.offer.time_to_ownership_in_days, 2)
        assert addon.principal == 7
        assert addon.downpayment == 3
        flush()
        assert offer.last_version.lead_addons.count() == 1

        ClientCreator.post_payment({
            "transaction_id": "Test3423423434245",
            "sender_name": lead.full_name,
            "sender_msisdn": lead.person.contactPhone.number,
            "amount": lead.downpayment,
            "memo": lead.future_contract_reference
        }, api_client, good_api_key)
        client = ClientCreator.register_lead(api_client, good_api_key, lead)

        assert client.contracts.select().first().contract_events.select(lambda e: e.type == ContractEventType.reference_pricing_change).count() == 1
