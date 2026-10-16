from tests.base_test import BaseViewTest
from pony import orm
import pytest
from payg_loan_system.offers.models import Offer, OfferType


@orm.db_session
def get_offer(type=OfferType.loan):
    offer = orm.select(offer for offer in Offer if offer.type == type).first()
    return offer


class TestOfferListView(BaseViewTest):
    url = 'offers.list_offers'
    template = 'list_offers.html'


class TestViewOfferView(BaseViewTest):
    url = 'offers.view_offers'
    template = 'view_offers.html'

    @pytest.fixture(autouse=True)
    def _autouse_setup(self, templates, context):
        self.context = context
        self.templates = templates
        self.offer = get_offer()
        self.params = dict(offer_id=self.offer.id)
        
class TestViewOfferViewLump(BaseViewTest):
    url = 'offers.view_offers'
    template = 'view_offers.html'

    @pytest.fixture(autouse=True)
    def _autouse_setup(self, templates, context):
        self.context = context
        self.templates = templates
        self.offer = get_offer(OfferType.lump_sum)
        self.params = dict(offer_id=self.offer.id)

class TestViewOfferViewTime(BaseViewTest):
    url = 'offers.view_offers'
    template = 'view_offers.html'

    @pytest.fixture(autouse=True)
    def _autouse_setup(self, templates, context):
        self.context = context
        self.templates = templates
        self.offer = get_offer(OfferType.time_based)
        self.params = dict(offer_id=self.offer.id)

class TestAddOfferView(BaseViewTest):
    url = 'offers.add_offers'
    template = 'edit_offers.html'


class TestEditOfferView(BaseViewTest):
    url = 'offers.edit_offers'
    template = 'edit_offers.html'

    @pytest.fixture(autouse=True)
    def _autouse_setup(self, templates, context):
        self.context = context
        self.templates = templates
        self.offer = get_offer()
        self.params = dict(offer_id=self.offer.id)

class TestEditOfferViewLump(BaseViewTest):
    url = 'offers.edit_offers'
    template = 'edit_offers.html'

    @pytest.fixture(autouse=True)
    def _autouse_setup(self, templates, context):
        self.context = context
        self.templates = templates
        self.offer = get_offer(OfferType.lump_sum)
        self.params = dict(offer_id=self.offer.id)

class TestEditOfferViewTime(BaseViewTest):
    url = 'offers.edit_offers'
    template = 'edit_offers.html'

    @pytest.fixture(autouse=True)
    def _autouse_setup(self, templates, context):
        self.context = context
        self.templates = templates
        self.offer = get_offer(OfferType.time_based)
        self.params = dict(offer_id=self.offer.id)