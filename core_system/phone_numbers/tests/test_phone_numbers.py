from pony.orm import db_session
from core_system.phone_numbers.model import PhoneNumbers


class TestPhoneNumbers:
    @db_session
    def test_it_only_requires_a_number_to_be_instantiated(self):
        some_phone_number = '12345'

        try:
            PhoneNumbers(number=some_phone_number)
        except Exception as error:
            assert error == None
        else:
            assert True
