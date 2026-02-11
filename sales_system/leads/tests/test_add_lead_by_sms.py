from core_system.operational_entities.models import Village
from datetime import datetime
from pony.orm import db_session, commit
from mock import patch
from sales_system.leads.lead_sms_app import LeadCreatorSMS
from sales_system.lead_generator.model import LeadGenerator
from sales_system.lead_generator.tests.factories import LeadGeneratorFactory
from sales_system.leads.models.lead import Lead
from tests.factories.factories import UserFactory
from messages_system.services.message_service import MessageService


class TestLeadCreatorSMS:

    @classmethod
    @db_session
    def setup_method(cls):
        cls.VALID_VILLAGE_ID = Village.select().first().not_empty_code

    @db_session
    def test_init_with_wrong_parameters_format(self):
        user = LeadGeneratorFactory.generate_user_with_lead_generator()
        variables = 'Herber*West*12'
        reception_time = datetime.today()

        error = 'The registration request should be (without spaces): CREATELEAD# NAME * SURNAME * PHONE * VILLAGE_ID * STATUS.'

        status = LeadCreatorSMS.create(user, '+255123456789', variables, reception_time)

        assert error in MessageService.get_message(status)

    @db_session
    def test_create_lead_with_village_none(self):
        village_id = 0
        lead_generator = LeadGenerator.select(lambda lg: lg.person.user).first()
        user = lead_generator.person.user
        variables = 'Henry*Mumu*1112223334*{}*L'.format(village_id)
        reception_time = datetime.today()

        error = 'Invalid L0 entity ID.'

        status = LeadCreatorSMS.create(user, '+255123456789', variables, reception_time)

        assert error in MessageService.get_message(status)

    @db_session
    def test_create_lead_with_no_lead_generator(self):
        user = UserFactory.stub()
        lead_generator_number = '+255123456789'
        variables = 'Henry*Mumu*1112223334*{}*L'.format(self.VALID_VILLAGE_ID)
        reception_time = datetime.today()

        error = 'The current user does not have a lead generator associated.'

        status = LeadCreatorSMS.create(user, lead_generator_number, variables, reception_time)

        assert error in MessageService.get_message(status)

    @db_session
    def test_create_lead(self):
        lead_generator = LeadGenerator.select(lambda lg: lg.person.user).first()
        user = lead_generator.person.user
        lead_generator_number = '+255123456789'
        variables = 'Henry*Mumu*1112223359*{}*L'.format(self.VALID_VILLAGE_ID)
        reception_time = datetime.today()

        with patch.object(LeadCreatorSMS, '_get_lead_generator', return_value=lead_generator):
            expected_number_of_leads = Lead.select().count() + 1

            status = LeadCreatorSMS.create(user, lead_generator_number, variables, reception_time)
            commit()

            assert expected_number_of_leads == Lead.select().count(), status
            assert status['lead_name'] == 'Henry'
            assert status['lead_surname'] == 'Mumu'

    @db_session
    def test_create_lead_with_phone_linked_to_person(self):
        lead_generator = LeadGenerator.select(lambda lg: lg.person.user).first()
        user = lead_generator.person.user
        lead_number = '1112223334' # Same as the other lead we just made
        variables = 'Henry*Mama*{}*{}*L'.format(lead_number, self.VALID_VILLAGE_ID)
        reception_time = datetime.today()

        error = 'The phone number is already owned by someone else. Edit on the platform to solve the issue.'

        status = LeadCreatorSMS.create(user, '+255123456789', variables, reception_time)

        assert error in MessageService.get_message(status)

