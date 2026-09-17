from pony.orm import db_session
from core_system.phone_numbers.model import PhoneNumbers
from core_system.person.models.person_model import Person
from payg_loan_system.payments.models.wallet import PaymentWallet


class TestPhoneNumber:
    number = '+255123456788'

    @classmethod
    @db_session
    def teardown_method(cls):
        phone = PhoneNumbers.get(number=cls.number)

        if phone:
            phone.delete()

    @db_session
    def test_create_phone_number_without_account(self):
        phone = PhoneNumbers(number=self.number,
                             person=Person.select().first())

        assert PhoneNumbers.get(number=self.number)

    @db_session
    def test_create_phone_number_with_account(self):
        mpesa = PaymentWallet.select().first()
        phone = PhoneNumbers(number=self.number,
                             payment_wallet=mpesa,
                             person=Person.select().first())

        phone_number = PhoneNumbers.get(number=self.number)
        assert phone_number
        assert mpesa.id == phone_number.payment_wallet.id
