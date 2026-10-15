from datetime import datetime
from pony.orm import db_session
import pytest
from sales_system.leads.models.lead_status import LeadStatus
from sales_system.leads.models.status_category import StatusCategory
from sales_system.leads.models.lead import Lead
from core_system.person.models.person_model import Person
from sales_system.leads.services.lead_status_change_service import LeadStatusChangeService
from shared.helpers.client_creator import ClientCreator


class TestLead:

    @pytest.fixture
    def lead(self):
        with db_session:
            return ClientCreator.create_lead(lead_data={
                'name': 'Test',
                'surname': 'Tst'
            })

    @pytest.fixture
    @db_session
    def lead_two(self):
        return ClientCreator.create_lead(lead_data={
            'name': 'Johnny',
            'surname': 'Siman',
            'phone_numbers': ['+505123123123']
        })

    @db_session
    def test_has_client_returns_false(self, lead):
        assert not lead.has_client()

    @pytest.mark.skip(reason='this test cannot run isolated')
    @db_session
    def test_has_client_returns_true(self):
        person = Person.select().first()

        lead = Lead(person=person,
                    receptionTime=datetime.today(),
                    statusUpdate=datetime.today())

        assert lead.has_client()

    @db_session
    def test_set_status_save_history(self):
        lead = Lead.select().first()
        LeadStatusChangeService._set_first_of_category(lead, StatusCategory.awaiting_information)

        assert lead.status_changes_history.select().count() == 1

        last_status = lead.status_changes_history.select().first()
        assert last_status.status == LeadStatus.get_first(StatusCategory.awaiting_information).name

    @db_session
    def test_get_last_contact_if_modified(self):
        lead = ClientCreator.create_lead(lead_data={
            'name': 'Johnny',
            'surname': 'Siman'
        })
        assert lead.get_last_contact() == lead.modifiedDate

