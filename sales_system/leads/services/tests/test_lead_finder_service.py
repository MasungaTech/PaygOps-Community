from pony.orm import db_session, desc, flush
from core_system.person.models.person_model import Person
from sales_system.leads.tests.factories import LeadFactory, PersonFactory
from sales_system.leads.services.lead_finder_service import LeadFinderService


class TestLeadFinderService:

    @db_session
    def test_find_leads_matching_payment_returns_lead(self):
        flush()
        latest_person_id = Person.select().order_by(desc(Person.id)).first().id
        PersonFactory.reset_sequence(latest_person_id+100)
        expected_lead = LeadFactory.stub(reporter=None)
        expected_lead.awaiting_payment = True
        lead = LeadFinderService.find_leads_awaiting_payment_matching_person(expected_lead.person)
        assert expected_lead == lead

    @db_session
    def test_find_leads_matching_payment_returns_none(self):
        expected_lead = LeadFactory.stub(reporter=None)
        expected_lead.awaiting_payment = False
        lead = LeadFinderService.find_leads_awaiting_payment_matching_person(expected_lead.person)
        assert lead is None
        assert LeadFinderService.find_leads_awaiting_payment_matching_person(None) is None
