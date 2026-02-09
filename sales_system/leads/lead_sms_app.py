from pony.orm import db_session
from sales_system.leads.services.add_lead_service import AddLeadService, Error
from sales_system.leads.models.lead_status import LeadStatus
from sales_system.leads.models.status_category import StatusCategory
from shared.services.settings_service import SettingsService


class LeadCreatorSMS:

    @classmethod
    @db_session
    def create(self, user, from_number, variables, reception_time):
        params = variables.split('*')

        if len(params) < 5:
            return {'success': False,
                    'status': 'INVALID_USER_COMMAND',
                    'proper_command_syntax': 'CREATELEAD# NAME * SURNAME * PHONE * VILLAGE_ID * STATUS'}

        self.user = user
        self.from_number = from_number
        self.name = params[0]
        self.surname = params[1]
        self.lead_phone_number = '+{}{}'.format(SettingsService.get_setting('PhoneExtension'), params[2])
        self.village_id = params[3]
        self.lead_status = params[4]#to be removed
        self.reception_time = reception_time

        lead_generator = self._get_lead_generator()
        if lead_generator is None:
            return {'success': False,
                    'status': 'USER_HAS_NO_LEAD_GENERATOR'}

        lead_data = {
            'name': self.name,
            'surname': self.surname,
            'village': self.village_id,
            'generator': lead_generator.id,
            'status': LeadStatus.get_first(StatusCategory.to_be_convinced).id,
            'phone_numbers': [self.lead_phone_number],
            'gender': 'undefined',
            'preferred_phone_number': self.lead_phone_number
        }
        try:
            lead = AddLeadService.add_lead(lead_data, self.user)
            return {'success': True,
                    'status': 'LEAD_CREATED_SMS_SUCCESS',
                    'lead_name': lead.person.name,
                    'lead_surname': lead.person.surname}
        except Error as error:
            if 'INVALID_VILLAGE_ID' in str(error):
                return {'success': False,
                        'status': 'INVALID_VILLAGE_ID'}
            if 'PHONE_NUMBER_ALREADY_OWNED' in str(error):
                return {'success': False,
                        'status': 'PHONE_NUMBER_ALREADY_OWNED'}
            else:
                return {**{'success': False,
                        'status': str(error)}, **error.data}

    @classmethod
    @db_session
    def _get_lead_generator(self):
        if self.user.person is not None:
            return self.user.person.leadGenerator
        else:
            return None
