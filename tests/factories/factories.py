from core_system.operational_entities.models import Village
from payg_loan_system.contracts.models.contract_status import ContractStatus
import factory
from functools import partial
from datetime import datetime
from payg_loan_system.payments.models.payment import Payment
from payg_loan_system.payments.models.wallet import PaymentWallet, PaymentWalletType
from core_system.person.models.person_model import Person
from core_system.client.models import Client
from core_system.users.models.user_model import User
from core_system.phone_numbers.model import PhoneNumbers
from payg_loan_system.reversed_payments.models import ReversedPayment
from tests.support.mock_query import MockQuery
from mock import Mock
from pony.orm import db_session


class AbstractPaymentFactory:
    @staticmethod
    def create():
        return PaymentFactory.stub(
                PaymentWallet=PaymentWalletFactory.stub(
                    client=ClientFactory.stub(
                        person=PersonFactory.stub())))

    @staticmethod
    def create_no_client():
        return PaymentFactory.stub(
            PaymentWallet=PaymentWalletFactory.stub(client=None))


class AbstractClientFactory:
    @staticmethod
    def create():
        return ClientFactory.stub(
            person=PersonFactory.stub())


class AbstractMpesaFactory:
    @staticmethod
    def create():
        return PaymentWalletFactory.stub(
                    client=ClientFactory.stub(
                        person=PersonFactory.stub()))

    @staticmethod
    def create_no_client():
        return PaymentWalletFactory.stub()


class AbstractUserFactory:
    @staticmethod
    def create(authorized=True):
        return UserFactory.stub(person=PersonFactory.stub(),
                                can_access=Mock(return_value=authorized))


class PaymentWalletFactory(factory.Factory):
    class Meta:
        model = PaymentWallet

    RegistrationDate = datetime.today()
    FullName = factory.Sequence(lambda n: 'ACCOUNT%d' % n)
    Type = PaymentWalletType.mobile_money
    client = None

    @classmethod
    def stub(cls, *args, **kwargs):
        account = super().stub(*args, **kwargs)
        account.get_last_payment = Mock(return_value=PaymentFactory.stub(Amount=10000))
        return account


class PaymentFactory(factory.Factory):
    class Meta:
        model = Payment

    Amount = 1000
    Reference = factory.Sequence(lambda n: 'TESTREF%d' % n)
    PaymentTime = datetime.today()
    PaymentReceptionTime = datetime.today()
    PaymentWallet = factory.SubFactory(PaymentWalletFactory)

    @classmethod
    def stub(cls, *args, **kwargs):
        payment = super().stub(*args, **kwargs)
        payment.remaining = payment.Amount
        return payment


class ReversedPaymentFactory(factory.Factory):
    class Meta:
        model = ReversedPayment

    reference_code = factory.Sequence(lambda n: 'TESTREF%d' % n)
    payment_code = factory.Sequence(lambda n: 'TESTPAYCODE%d' % n)
    amount = 2000
    reversed_on = datetime.today()
    received_on = datetime.now()

class PhoneNumbersFactory(factory.Factory):
    class Meta:
        model = PhoneNumbers
    
    number = '+0111222333'
    
    @classmethod
    def stub(cls, *args, **kwargs):
       return super().stub(*args, **kwargs)
    
class FakeVillage:
    id = 123
        
class PersonFactory(factory.Factory):
    class Meta:
        model = Person

    id = factory.Sequence(lambda n: n+200)
    name = factory.Sequence(lambda n: 'P{}'.format(n))
    surname = factory.Sequence(lambda n: 'S{}'.format(n))
    type = 1
    modifiedDate = datetime.today()
    leadGenerator = None
    client = None
    village = None
    client_group = None
    sms_language = 'EN'
    contactPhone = None
    phoneNumbers = []
    lead = MockQuery([])

    @classmethod
    @db_session
    def stub(cls, *args, **kwargs):
        person = super().stub(*args, **kwargs)
        person.full_name = str(person.name) + ' ' + str(person.surname)
        person.get_sms_language = Mock(return_value='EN')
        person.preferred_phone_number = partial(Person.preferred_phone_number, person)
        person.village = Village.select().first()
        return person


class ClientFactory(factory.Factory):
    class Meta:
        model = Client

    id = factory.Sequence(lambda n: n+1000)
    person = factory.SubFactory(PersonFactory)
    modifiedDate = datetime.today()
    RegistrationDate = datetime.now()
    contracts = MockQuery([])
    
    @classmethod
    def stub(cls, *args, **kwargs):
        client = super().stub(*args, **kwargs)
        client.full_name = ''
        client.get_payment_accounts = partial(Client.get_payment_accounts, client)
        client.GetDevices = partial(Client.GetDevices, client)
        client.termination_date = None
        client.__class__.first_active_contract = property(Client.first_active_contract.__get__)
        client.__class__.first_active_or_late_contract = property(Client.first_active_or_late_contract.__get__)
        client.__class__.active_contracts = property(Client.active_contracts.__get__)
        client.__class__.active_or_late_contracts = property(Client.active_or_late_contracts.__get__)
        return client


class UserFactory(factory.Factory):
    class Meta:
        model = User
    id = factory.Sequence(lambda n: n)
    person = factory.SubFactory(PersonFactory)
    AuthorizationLevel = 1
    username = 'user@test.com'
    password = 'test1234'
    shop = 1
    mentorID = None
    loginExpirationDate = None

    @classmethod
    def stub(cls, *args, **kwargs):
        user = super().stub(*args, **kwargs)
        user.is_expired = partial(User.is_expired, user)
        user.full_name = ''
        user.reload = lambda: user
        user.can_access_in_all = lambda p: True
        return user
