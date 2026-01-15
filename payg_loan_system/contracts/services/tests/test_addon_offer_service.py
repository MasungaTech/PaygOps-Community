from payg_loan_system.contracts.models.addon_category import AddOnCategory
from pony.orm import db_session
import pytest
from payg_loan_system.contracts.models.addons_model import AddOnType
from payg_loan_system.contracts.services.addons.addon_offer_service import AddonOfferService
from payg_loan_system.contracts.services.addon_service import AddonService
from payg_loan_system.contracts.services.addons.addon_offer_version_service import AddonOfferVersionService
from payg_loan_system.offers.models import Offer
from core_system.users.services.user_getter_service import UserGetterService
from shared.helpers.client_creator import ClientCreator
from shared.logger.loggers import Error


class TestAddonOfferService:

    @db_session
    def test_payment_and_category_mode_helper(self):

        assert AddOnType.valid('Lump-Sum')
        assert AddOnType.valid('Loan Extension')
        assert not AddOnType.valid('NotValidPaymentMode')
        
        assert AddOnCategory.get(name="Product")
        assert AddOnCategory.get(name="Service")
        assert not AddOnCategory.get(name="NotValidCategory")
    
    @db_session
    def test_create_addon_offers(self, super_admin_user):
        
        user = super_admin_user()
        ## Correct use works
        AddonOfferService.create(user, "OFFER 1", "OFFER1", "200", AddOnCategory.get(name="Product"), AddOnType.lump_sum)
        # same name on purpose
        AddonOfferService.create(user, "OFFER 1", "OFFER2", "200.00", AddOnCategory.get(name="Product"), AddOnType.lump_sum)
        AddonOfferService.create(user, "OFFER 3", "OFFER3", 200.00, AddOnCategory.get(name="Product"), AddOnType.lump_sum)
        AddonOfferService.create(user, "OFFER 4", "OFFER4", 200.0, AddOnCategory.get(name="Product"), AddOnType.lump_sum)
        AddonOfferService.create(user, "OFFER 5", "OFFER5", "200.0", AddOnCategory.get(name="Service"), AddOnType.loan)
        AddonOfferService.create(user, "OFFER 6", "OFFER6", 200.000, AddOnCategory.get(name="Service"), AddOnType.loan)
        AddonOfferService.create(user, "OFFER 7", "OFFER7", "200.000", AddOnCategory.get(name="Service"), AddOnType.loan, available=True) 
        AddonOfferService.create(user, "OFFER 8", "OFFER8", 200, AddOnCategory.get(name="Service"), AddOnType.loan, available=False)
        AddonOfferService.create(user, "OFFER 9", "OFFER9", 200, AddOnCategory.get(name="Service"), AddOnType.loan)
        AddonOfferService.create(user, "OFFER 10", "OFFER10", 200, AddOnCategory.get(name="Service"), AddOnType.loan, True)
        
        ## Validation checks
        self._create_fails(user, "ADDON_OFFER_CODE_HAS_SPACES", "OFFER 1", "OFFER 11", "200.00", AddOnCategory.get(name="Product"), AddOnType.lump_sum)
        self._create_fails(user, "ADDON_OFFER_CODE_ALREADY_EXISTS", "OFFER 1", "OFFER2", "200.00", AddOnCategory.get(name="Product"), AddOnType.lump_sum)
        self._create_fails(user, "INVALID_AMOUNT_TOO_MANY_DIGITS", "OFFER 1", "OFFER12", "200.001", AddOnCategory.get(name="Product"), AddOnType.lump_sum)
        self._create_fails(user, "INVALID_CATEGORY", "OFFER 1", "OFFER13", "200.00", "not a category", AddOnType.lump_sum)
        self._create_fails(user, "INVALID_ADDON_OFFER_TYPE", "OFFER 1", "OFFER14", "200.00", AddOnCategory.get(name="Product"), 'InvalidPaymentMode')

    @db_session
    def test_edit_and_delete_addon_offers(self, api_client, good_api_key, super_admin_user):
        
        offer = AddonOfferService.create(super_admin_user(), "OFFER Test", "OFFERTEST", "200", AddOnCategory.get(name="Product"), AddOnType.lump_sum)
        offer_version = offer.last_version

        AddonOfferVersionService.make_available(offer_version)
        assert offer_version.available_for_registration
        AddonOfferVersionService.make_unavailable(offer_version)
        assert not offer_version.available_for_registration
        
        with pytest.raises(Exception) as excinfo:
            AddonOfferVersionService.make_unavailable(offer_version)
        assert 'ADDON_OFFER_ALREADY_UNAVAILABLE' in str(excinfo)
        
        AddonOfferVersionService.make_available(offer_version)
        with pytest.raises(Exception) as excinfo:
            AddonOfferVersionService.make_available(offer_version)
        assert 'ADDON_OFFER_ALREADY_AVAILABLE' in str(excinfo)
        
        user = UserGetterService.get_by_username("super_admin@test.com")
        contract = ClientCreator.create(api_client, good_api_key).contracts.select().first()
        addon = AddonService.create(contract, offer_version, 1, user)
        with pytest.raises(Exception) as excinfo:
            AddonOfferService.delete_from_object_and_user(offer, user)
        assert 'ADDON_OFFER_HAS_ADDONS' in str(excinfo)
        with pytest.raises(Exception) as excinfo:
            AddonOfferVersionService.delete_from_object_and_user(offer_version, user)
        assert 'ADDON_OFFER_HAS_ADDONS' in str(excinfo)
        
        addon.delete()
        AddonOfferVersionService.delete_from_object_and_user(offer_version, user)
        AddonOfferService.delete_from_object_and_user(offer, user)
        
    @staticmethod
    def _create_fails(user, error, *args, **kwargs):
        with pytest.raises(Error) as excinfo:
            AddonOfferService.create(user, *args, **kwargs)
        assert error in str(excinfo)