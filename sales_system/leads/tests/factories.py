from datetime import datetime
from tests.support.mock_query import MockQuery
import factory
from mock import Mock
from functools import partial
from tests.factories.factories import PersonFactory, ClientFactory, UserFactory, PhoneNumbersFactory
from sales_system.leads.models.lead import Lead
from payg_loan_system.offers.tests.factories import TimeOfferFactory


class LeadFactory(factory.Factory):
    class Meta:
        model = Lead

    person = factory.SubFactory(PersonFactory)
    decision = True
    receptionTime = datetime.today()
    contacted = True
    statusUpdate = datetime.today()
    reporter = factory.SubFactory(UserFactory)
    portfolio = None
    offer = TimeOfferFactory.stub()
    id = factory.Sequence(lambda n: n)
    future_contract_reference = 'C88880224'
    loan_addons_downpayments = 0
    addons = MockQuery([])
    reconciled_payments = []
    decisionMaker = factory.SubFactory(UserFactory)
    forms_answered = []
    offer_editing_locked = True
    forms_missing_for_registration = []

    @classmethod
    def stub(cls, *args, **kwargs):
        lead = super().stub(*args, **kwargs)
        lead.__class__.inactive = property(Lead.inactive.__get__)
        lead.discarded = False
        lead.__class__.to_be_convinced = property(Lead.to_be_convinced.__get__)
        lead.__class__.awaiting_information = property(Lead.awaiting_information.__get__)
        lead.__class__.awaiting_decision = property(Lead.awaiting_decision.__get__)
        lead.awaiting_payment = False
        lead.awaiting_delivery = False
        lead.installed = "client" in kwargs
        lead.deposit_paid = False
        lead.active = False
        lead.get_offer = partial(Lead.get_offer, lead)
        lead.person.lead = [lead]
        lead.generator = Mock(id=92)
        lead.get_number_installments = Mock(return_value=365)
        lead.__class__.downpayment = property(Lead.downpayment.__get__)
        lead.__class__.lump_sum_addons_value = 0
        lead.__class__.lump_sum_addons = property(Lead.lump_sum_addons.__get__)
        lead.get_serialized_object = Mock(return_value={})
        return lead

class AbstractLeadFactory:

    @staticmethod
    def create(offer=None):
        if offer is None:
            offer = TimeOfferFactory.stub()
        lead = LeadFactory.stub(
            person=PersonFactory.stub(
            client=ClientFactory.stub()),
            offer=offer)
        lead.person.lead = [lead]
        lead.installed = True
        lead.deposit_paid = True
        lead.offer_editing_locked = True
        return lead

    @staticmethod
    def create_no_client(offer=None, no_offer=False):
        if offer is None:
            offer = TimeOfferFactory.stub()
        if no_offer:
            offer = None
        lead = LeadFactory.stub(
            person=PersonFactory.stub(contactPhone=PhoneNumbersFactory.stub()),
            offer=offer)

        lead.deposit_paid = False
        lead.offer_editing_locked = True

        return lead
