from core_system.operational_entities.models import Village
from datetime import datetime
from mock import patch
from pony import orm
from messages_system.services.send_sms import SMSSend
from messages_system.services.user_sms_handler import enter_lead_command_handler
from core_system.users.models.user_model import User
from tests.factories import user_mock


@patch.object(SMSSend, 'SendMessage')
class TestEnterLeadCommandHandler:
    LEAD_GENERATOR_NUMBER = '+2349876543211' # From the database seeder

    @classmethod
    def setup_class(cls):
        user_mock.create_user_with_lead_generator()

    @orm.db_session
    def test_enter_lead_with_empty_variables(self, message_mock):
        LEAD_GENERATOR_USER = User.get(username='agent2@test.com')
        enter_lead_command_handler(LEAD_GENERATOR_USER, self.LEAD_GENERATOR_NUMBER,
                                   '', datetime.today())

        error = 'The registration request should be (without spaces): CREATELEAD# NAME * SURNAME * PHONE * VILLAGE_ID * STATUS.'

        message_mock.assert_called_once_with(self.LEAD_GENERATOR_NUMBER, error, LEAD_GENERATOR_USER.person)

    @orm.db_session
    def test_enter_lead_with_wrong_variables(self, message_mock):
        LEAD_GENERATOR_USER = User.get(username='agent2@test.com')
        enter_lead_command_handler(LEAD_GENERATOR_USER,
                                   self.LEAD_GENERATOR_NUMBER,
                                   'CREATELEAD#Henry*Mumu*0673636699*1',
                                   datetime.today())

        error = 'The registration request should be (without spaces): CREATELEAD# NAME * SURNAME * PHONE * VILLAGE_ID * STATUS.'

        message_mock.assert_called_once_with(self.LEAD_GENERATOR_NUMBER, error, LEAD_GENERATOR_USER.person)

    @orm.db_session
    def test_enter_lead_with_village_none(self, message_mock):
        LEAD_GENERATOR_USER = User.get(username='agent2@test.com')
        village_id = 0
        message = 'CREATELEAD#Henry*Mumu*1112223335*{}*L'.format(village_id)

        enter_lead_command_handler(LEAD_GENERATOR_USER,
                                   self.LEAD_GENERATOR_NUMBER,
                                   message,
                                   datetime.today())

        error = 'Invalid L0 entity ID.'

        message_mock.assert_called_once_with(self.LEAD_GENERATOR_NUMBER, error, LEAD_GENERATOR_USER.person)

    @orm.db_session
    def test_enter_lead_success(self, message_mock):
        LEAD_GENERATOR_USER = User.get(username='agent2@test.com')
        message = 'CREATELEAD#Henry*Mumu*1112223335*'+str(Village.select().first().not_empty_code)+'*L'

        enter_lead_command_handler(LEAD_GENERATOR_USER,
                                   self.LEAD_GENERATOR_NUMBER,
                                   message,
                                   datetime.today())

        message = 'Lead CREATELEAD#Henry Mumu was created.'

        message_mock.assert_called_once_with(self.LEAD_GENERATOR_NUMBER, message, LEAD_GENERATOR_USER.person)

    @orm.db_session
    def test_enter_lead_with_phone_linked_to_person(self, message_mock):
        LEAD_GENERATOR_USER = User.get(username='agent2@test.com')
        lead_number = '1112223335'
        village = Village.select().first()
        message = 'CREATELEAD#Henry*Mama*{}*{}*L'.format(lead_number, village.not_empty_code)

        enter_lead_command_handler(LEAD_GENERATOR_USER,
                                   self.LEAD_GENERATOR_NUMBER,
                                   message,
                                   datetime.today())

        error = 'The phone number is already owned by someone else. Edit on the platform to solve the issue.'

        message_mock.assert_called_once_with(self.LEAD_GENERATOR_NUMBER, error, LEAD_GENERATOR_USER.person)
