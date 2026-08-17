from uuid import uuid4

from config import API_PREFIX
from core_system.operational_entities.models import Hub
from core_system.person.models.person_model import Person, PersonType
from core_system.phone_numbers.model import PhoneNumbers
from core_system.role.methods.getters import get_role_from_name
from pony import orm
from shared.services.settings_service import SettingsService


class TestAddUserAPIPhoneNumbers:

    @staticmethod
    @orm.db_session
    def _phone_number():
        extension = str(SettingsService.get_setting('PhoneExtension'))
        phone_length = int(SettingsService.get_setting('PhoneLength'))
        local_number = str(uuid4().int % (10 ** phone_length)).zfill(phone_length)
        return '+' + extension + local_number

    @staticmethod
    @orm.db_session
    def _payload(phone_numbers, preferred_phone_number):
        suffix = uuid4().hex[:10]
        return {
            'language': 'EN',
            'name': 'API Phone',
            'password': 'Pvstar0000~',
            'password_confirm': 'Pvstar0000~',
            'phone_numbers': phone_numbers,
            'preferred_phone_number': preferred_phone_number,
            'reference_entity_id': Hub.select().first().id,
            'role_id': get_role_from_name('Agent').id,
            'surname': suffix,
            'username': 'api_phone_user_' + suffix,
        }

    @staticmethod
    @orm.db_session
    def _assign_phone_to_existing_person(phone_number):
        person = Person(name='Existing', surname='Owner', type=PersonType.client)
        phone = PhoneNumbers.get(number=phone_number)
        if not phone:
            phone = PhoneNumbers(number=phone_number)
        phone.persons.add(person)

    @staticmethod
    def _post_user(api_client, admin_api_key, payload):
        return api_client.post(
            API_PREFIX + '/users',
            json=payload,
            headers={'Authorization': 'Bearer ' + admin_api_key},
        )

    def test_create_user_rejects_preferred_phone_not_in_phone_numbers(self, api_client, admin_api_key):
        payload = self._payload(
            phone_numbers=[self._phone_number()],
            preferred_phone_number=self._phone_number(),
        )

        response = self._post_user(api_client, admin_api_key, payload)

        assert response.status_code == 400
        assert response.json['error'] == 'PREFERRED_PHONE_NOT_IN_PHONE_NUMBERS'
        assert 'preferred phone number' in response.json['error_message'].lower()

    def test_create_user_rejects_owned_preferred_phone_without_500(self, api_client, admin_api_key):
        owned_phone_number = self._phone_number()
        self._assign_phone_to_existing_person(owned_phone_number)
        payload = self._payload(
            phone_numbers=[self._phone_number()],
            preferred_phone_number=owned_phone_number,
        )

        response = self._post_user(api_client, admin_api_key, payload)

        assert response.status_code == 400
        assert response.json['error'] == 'PHONE_NUMBER_ALREADY_OWNED'
        assert 'already owned' in response.json['error_message']

    def test_create_user_with_included_preferred_phone_succeeds(self, api_client, admin_api_key):
        preferred_phone_number = self._phone_number()
        payload = self._payload(
            phone_numbers=[preferred_phone_number, self._phone_number()],
            preferred_phone_number=preferred_phone_number,
        )

        response = self._post_user(api_client, admin_api_key, payload)

        assert response.status_code == 201
        assert response.json['preferred_phone_number'] == preferred_phone_number
        assert sorted(response.json['phone_numbers']) == sorted(payload['phone_numbers'])
