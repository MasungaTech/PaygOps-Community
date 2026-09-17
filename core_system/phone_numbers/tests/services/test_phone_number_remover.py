from pony import orm
from pony.orm.core import flush
import pytest

from core_system.phone_numbers.helpers import remove_number
from core_system.phone_numbers.model import PhoneNumbers
from core_system.phone_numbers.services.phone_number_getter import \
    PhoneNumberGetterService
from core_system.person.models.person_model import Person
from core_system.role.models import Permission
from sales_system.leads.services.edit_lead_service import EditLeadService
from shared.helpers.client_creator import ClientCreator
from shared.logger.loggers import Error
from shared.services.settings_service import SettingsService


class TestPhoneNumberRemover:


    @orm.db_session
    def _create_phonenumber(self):
        PhoneNumbers(
            number='some_number',
            person=1
        )

    @orm.db_session
    def _retrieve_test_person_phonenumbers(self):
        phonenumbers = Person.get(id=1).phoneNumbers

        data = map(lambda phonenumber: phonenumber.number, phonenumbers)
        return list(data)

    @orm.db_session
    def test_remove_phone_respect_settings_and_permission(self, admin_user):

        lead = ClientCreator.create_lead()
        assert lead.person.contactPhone in lead.person.phoneNumbers
        user = admin_user()

        flush()
        phones = [n.number for n in lead.person.phoneNumbers]
        EditLeadService.edit_lead(lead, {'phone_numbers': []}, user)

        assert lead.person.phoneNumbers.count() == 0
        for phone in phones:
            leftover = PhoneNumbers.get(number=phone)
            assert leftover is not None
            assert leftover.persons.count() == 0
            assert leftover not in PhoneNumberGetterService.find_phone_numbers(phone.replace('+', ''))
        EditLeadService.edit_lead(lead, {'phone_numbers': phones}, user)
        assert lead.person.phoneNumbers.count() == 1

        config = SettingsService.get_setting('LeadInfoSettings')
        config['phone_number'].update({
            'required': True
        })
        SettingsService.set_setting('LeadInfoSettings', config)
        EditLeadService.edit_lead(lead, {'phone_numbers': []}, user)

        assert lead.person.phoneNumbers.count() == 0
        EditLeadService.edit_lead(lead, {'phone_numbers': phones}, user)
        assert lead.person.phoneNumbers.count() == 1

        permission = Permission.get(code_name="RemoveLastPhoneNumbers")
        user.AuthorizationLevel.permissions.remove(permission)
        assert not user.can_access('RemoveLastPhoneNumbers', lead.person)
        with pytest.raises(Error) as error:
            EditLeadService.edit_lead(lead, {'phone_numbers': []}, user)
        assert error.value.code == 'LAST_PHONE_REMOVAL_FORBIDDEN'
        config = SettingsService.get_setting('LeadInfoSettings')
        config['phone_number'].update({
            'required': False
        })
        SettingsService.set_setting('LeadInfoSettings', config)
        user.AuthorizationLevel.permissions.add(permission)

    @orm.db_session
    def test_remove_phone_keeps_number_if_another_person_still_owns_it(self, admin_user):
        config = SettingsService.get_setting('LeadInfoSettings')
        config['phone_number'].update({
            'required': False
        })
        SettingsService.set_setting('LeadInfoSettings', config)

        lead = ClientCreator.create_lead()
        other_lead = ClientCreator.create_lead()
        phone = lead.person.phoneNumbers.select().first()
        number = phone.number
        phone.persons.add(other_lead.person)
        flush()

        remove_number(number, admin_user(), lead.person)

        kept = PhoneNumbers.get(number=number)
        assert kept is not None
        assert other_lead.person in kept.persons
        assert lead.person not in kept.persons
