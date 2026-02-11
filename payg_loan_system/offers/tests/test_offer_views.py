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

    @classmethod
    @orm.db_session
    @pytest.fixture(autouse=True)
    def setup_method(cls, templates, context):
        cls.context = context
        cls.templates = templates
        cls.offer = get_offer()
        cls.params = dict(offer_id=cls.offer.id)
        
class TestViewOfferViewLump(BaseViewTest):
    url = 'offers.view_offers'
    template = 'view_offers.html'

    @classmethod
    @orm.db_session
    @pytest.fixture(autouse=True)
    def setup_method(cls, templates, context):
        cls.context = context
        cls.templates = templates
        cls.offer = get_offer(OfferType.lump_sum)
        cls.params = dict(offer_id=cls.offer.id)

class TestViewOfferViewTime(BaseViewTest):
    url = 'offers.view_offers'
    template = 'view_offers.html'

    @classmethod
    @orm.db_session
    @pytest.fixture(autouse=True)
    def setup_method(cls, templates, context):
        cls.context = context
        cls.templates = templates
        cls.offer = get_offer(OfferType.time_based)
        cls.params = dict(offer_id=cls.offer.id)

class TestAddOfferView(BaseViewTest):
    url = 'offers.add_offers'
    template = 'edit_offers.html'


class TestEditOfferView(BaseViewTest):
    url = 'offers.edit_offers'
    template = 'edit_offers.html'

    @classmethod
    @orm.db_session
    @pytest.fixture(autouse=True)
    def setup_method(cls, templates, context):
        cls.context = context
        cls.templates = templates
        cls.offer = get_offer()
        cls.params = dict(offer_id=cls.offer.id)

class TestEditOfferViewLump(BaseViewTest):
    url = 'offers.edit_offers'
    template = 'edit_offers.html'

    @classmethod
    @orm.db_session
    @pytest.fixture(autouse=True)
    def setup_method(cls, templates, context):
        cls.context = context
        cls.templates = templates
        cls.offer = get_offer(OfferType.lump_sum)
        cls.params = dict(offer_id=cls.offer.id)

class TestEditOfferViewTime(BaseViewTest):
    url = 'offers.edit_offers'
    template = 'edit_offers.html'

    @classmethod
    @orm.db_session
    @pytest.fixture(autouse=True)
    def setup_method(cls, templates, context):
        cls.context = context
        cls.templates = templates
        cls.offer = get_offer(OfferType.time_based)
        cls.params = dict(offer_id=cls.offer.id)