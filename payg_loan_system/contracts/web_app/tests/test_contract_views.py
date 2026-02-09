from payg_loan_system.contracts.models.addon_category import AddOnCategory
from tests.base_test import BaseViewTest
from pony import orm
import pytest
from payg_loan_system.contracts.services.tests.factories import TestContractCreator, Contract
from payg_loan_system.contracts.services.addons.addon_offer_service import AddonOfferService
from payg_loan_system.contracts.models.addons_model import AddOnOffer, AddOnType


@orm.db_session
def get_contract():
    contract = orm.select(contract for contract in Contract).first()
    if not contract:
        contract = TestContractCreator.create_test_contract('test_contract_view', create_first_repayment=False)
    return contract

@orm.db_session
def get_addon_offer(user):
    code = 'TESTADDONSVIEWS'
    offer = AddOnOffer.get(code="TESTADDONSVIEWS")
    if not offer:
        offer = AddonOfferService.create(user, 't', code, "10.1", AddOnCategory.get(name="Service"), AddOnType.lump_sum, True)
        orm.flush()
        return offer
    else:
        return offer

class TestContractListView(BaseViewTest):
    url = 'contract.list_contracts'
    template = 'list_contracts.html'


class TestViewContractView(BaseViewTest):
    url = 'contract.view_contract'
    template = 'view_contract.html'

    @classmethod
    @orm.db_session
    @pytest.fixture(autouse=True)
    def setup_method(cls, templates, context):
        cls.context = context
        cls.templates = templates
        cls.contract = get_contract()
        cls.params = dict(contract_reference=cls.contract.reference)


class TestContractDashboardView(BaseViewTest):
    redirect = True
    url = 'contract.view_contract_dashboard'
    template = 'view_contract_dashboard.html'
    
class TestAddonOffersListView(BaseViewTest):
    url = 'contract.addons_configuration'
    template = 'addons_configuration.html'
    
class TestAddonOffersAddView(BaseViewTest):
    url = 'contract.add_addon_offer'
    template = 'edit_addon_offer.html'
    
class TestViewAddonOferView(BaseViewTest):
    url = 'contract.view_addon_offer'
    template = 'view_addon_offer.html'

    @classmethod
    @orm.db_session
    @pytest.fixture(autouse=True)
    def setup_method(cls, templates, context, super_admin_user):
        cls.context = context
        cls.templates = templates
        with orm.db_session:
            cls.offer = get_addon_offer(super_admin_user())
        cls.params = dict(offer_id=cls.offer.id)
        
class TestEditAddonOferView(BaseViewTest):
    url = 'contract.edit_addon_offer'
    template = 'edit_addon_offer.html'

    @classmethod
    @orm.db_session
    @pytest.fixture(autouse=True)
    def setup_method(cls, templates, context, super_admin_user):
        cls.context = context
        cls.templates = templates
        with orm.db_session:
            cls.offer = get_addon_offer(super_admin_user())
        cls.params = dict(offer_id=cls.offer.id)
        
