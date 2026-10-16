from pony.orm import db_session
from core_system.phone_numbers.helpers import save_phone_number, \
    add_number
from core_system.person.models.person_model import Person
from core_system.phone_numbers.model import PhoneNumbers
import mock


class PhoneNumberTests:
    @db_session
    def test_save_phone_number_to_person(self):
        person = Person.select().first()
        phone = PhoneNumbers.all().first()

        res, string = save_phone_number(phone.id, person.id)

        assert res == phone
        assert res.person == person
        assert " assigned to " in string


    @db_session
    @mock.patch('core_system.phone_numbers.helpers.get_owned_phone_number_message', return_value='Phone number exits')
    def test_add_phone_number(self, *args):
        person = Person.select().first()
        phone = '+255123456784'
        res = add_number(phone, person)

        assert not res['duplicate']

        res = add_number(phone, person)
        assert res['duplicate']
