from core_system.users.models.user_model import User
from core_system.operational_entities.models import Village
import pytest
from pony import orm

from sales_system.leads.models.lead import Lead
from sales_system.leads.services.update_lead_service import UpdateLeadService

class TestUpdateLeadService:
    @orm.db_session
    def test_it_updates_leads(self):
        lead_to_update = Lead.get(id=3)
        assert(lead_to_update.person.name == 'Test')
        some_descriptor = self._generate_descriptor()

        UpdateLeadService.update(some_descriptor, User.get(id=1))

        assert(lead_to_update.person.name == 'iluminati')

    def _generate_descriptor(self):
        ready_to_buy_status = 12

        return {
            'id': 3,
            'name': 'iluminati',
            'surname': 'pequeñito',
            'gender': 'male',
            'phone_number': 'ten_digits_number',
            'generator': 1,
            'village': Village.select().first().not_empty_code,
            'modified_date': '2000-01-01T10:00:00.000Z',
            'entry_date': '2000-01-01T10:00:00.000Z',
            'status': ready_to_buy_status,
            'home_use': True,
            'business_use': True,
        }
