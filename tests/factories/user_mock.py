from core_system.role.models import Role
from core_system.operational_entities.models import Village
from datetime import datetime
from random import randint
import uuid
from pony.orm import db_session, flush

from core_system.core_entities import db
from core_system.users.models.user_model import User
from core_system.users.services.edit_user_service import EditUserService
from payg_loan_system.contracts.models.addon_category import AddOnCategory
from payg_loan_system.contracts.models.addons_model import AddOnType
from payg_loan_system.contracts.services.addons.addon_offer_service import AddonOfferService
from payg_loan_system.contracts.services.addon_service import AddonService
from payg_loan_system.devices.model.offline_token_model import OfflineToken, TokenType
from payg_loan_system.offers.services.create_offer_service import CreateOfferService
from payg_loan_system.transaction_requests.models import TransactionRequest
from sales_system.lead_generator.model import LeadGenerator
from sales_system.leads.models.lead_status import LeadStatus
from sales_system.leads.models.lead import Lead
from sales_system.leads.services.add_lead_service import AddLeadService
from sales_system.leads.services.lead_status_service import LeadStatusService
from shared.file_upload.model import StoredFileType
from shared.file_upload.services.stored_file_service import StoredFileService
from shared.helpers.date_helper import random_date
from core_system.role.methods.getters import get_role_from_name
from core_system.person.models.person_model import Person, PersonType
from payg_loan_system.devices.model.device import Device
from core_system.phone_numbers.model import PhoneNumbers
from core_system.phone_numbers.services.add_phone_number_service import AddPhoneNumberService
from shared.services.settings_service import SettingsService
import config
from payg_loan_system.devices.services.create_device_service import DeviceCreateService


@db_session
def create_super_admin():
    headquarters_shop = db.Hub.get(name="Shop1")
    user = EditUserService.add_user(
        None,
        'Solaris', 'SuperAdmin', 'super_admin@test.com','test1234',
        get_role_from_name('SuperAdmin'),
        headquarters_shop
    )
    user.roles_in_entities.create(sync_entity=True)

@db_session
def create_admin():
    headquarters_shop = db.Hub.get(name="Shop2")
    user = EditUserService.add_user(
        None,
        'Solaris', 'Admin', 'admin@test.com', 'test1234',
        get_role_from_name('Admin'),
        headquarters_shop
    )
    user.roles_in_entities.create(sync_entity=True)

@db_session
def create_itmanager():
    headquarters_shop = db.Hub.get(name="Shop2")
    user = EditUserService.add_user(
        None,
        'Solaris it', 'Manager', 'admin@example.com', 'test1234',
        get_role_from_name('SuperAdmin'),
        headquarters_shop
    )
    user.roles_in_entities.create(entity=headquarters_shop, sync_entity=True)


@db_session
def create_agent():
    headquarters_shop = db.Hub.get(name="Shop3")
    user = EditUserService.add_user(
        None,
        'Solaris', 'Agent', 'agent@test.com', 'test1234',
        get_role_from_name('Agent'),
        headquarters_shop
    )
    return user


@db_session
def create_agent_2():
    AGENT_NUMBER_2 = '+2349876543222'
    headquarters_shop = db.Hub.get(name="Shop3")
    flush()
    print([role.name for role in Role.select()])
    assert get_role_from_name('SuperManager')
    user = EditUserService.add_user(
        None,
        'Solaris', 'Agent3', 'agent3@test.com', 'test1234',
        get_role_from_name('SuperManager'),
        headquarters_shop
    )
    user.roles_in_entities.create()
    flush()
    AddPhoneNumberService.set_preferred_number(AGENT_NUMBER_2, user.person)
    return user


@db_session
def create_view_only_user():
    headquarters_shop = db.Hub.get(name="Shop4")
    user = EditUserService.add_user(
        None,
        'Solaris', 'ViewOnly', 'view_only@test.com', 'test1234',
        get_role_from_name('ViewOnly'),
        headquarters_shop
    )
    user.roles_in_entities.create(sync_entity=True)
    return user


@db_session
def create_manager():
    headquarters_shop = db.Hub.get(name="Shop5")
    user = EditUserService.add_user(
        None,
        'Solaris', 'Manager', 'manager@test.com', 'test1234',
        get_role_from_name('Manager'),
        headquarters_shop
    )
    user.roles_in_entities.create(sync_entity=True)



@db_session
def create_lead_generator(p_id):
    person = Person.get(id=p_id)
    return LeadGenerator(person=person, type=2)

@db_session
def create_picture():
    return StoredFileService.create_without_file(
        type=StoredFileType.PICTURE,
        uuid='9633a987-b135-4132-8a23-36dfdbc97ff5'
    )


@db_session
def create_user_with_lead_generator():
    AGENT_NUMBER = '+2349876543211'
    headquarters_shop = db.Hub.get(name="Shop3")
    user = EditUserService.add_user(
        None,
        'Solaris', 'Agent2', 'agent2@test.com', 'test1234',
        get_role_from_name('Agent'),
        headquarters_shop
    )
    user.roles_in_entities.create(sync_entity=True)
    flush()
    AddPhoneNumberService.add_phone_numbers_to_person([AGENT_NUMBER], user.person)
    create_lead_generator(user.person.id)
    return user


@db_session
def create_user(name, surname, email, number, role_name):
    headquarters_shop = db.Village.select().first().parent.parent
    user = EditUserService.add_user(
        None,
        name, surname, email, 'test1234',
        get_role_from_name(role_name),
        headquarters_shop)
    flush()
    AddPhoneNumberService.add_phone_numbers_to_person([number], user.person)
    create_lead_generator(user.person.id)
    return user



@db_session
def create_lead(date=None, status_id=12, name='Test', surname='Lead888'):
    if not date:
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    village  = Village.select().first()
    person = Person(name=name, surname=surname, type=PersonType.lead, village=village)
    PhoneNumbers(number=create_fake_phone_number(), person=person)
    generator = LeadGenerator.get(id=1)
    new_lead = Lead(person=person,
                    generator=generator,
                    receptionTime=date,
                    status=LeadStatus.get(id=status_id),
                    statusUpdate=date,
                    entryDate=random_date(),
                    future_contract_reference="C000111222333")
    return new_lead


@db_session
def get_device(d_id):
    return Device.get(SerialNumber=str(d_id))


@db_session
def create_devices(num=10):
    for i in range(1, num):
        DeviceCreateService.create(serial_number=str(i),
                            mode=1,
                            device_type='SOL')

@db_session
def generate_offline_token():
    device = Device.select().first()
    OfflineToken(
        device=device,
        uuid=str(uuid.uuid1()),
        token='123456789',
        type=TokenType.add_credit,
        credit_value=0
    )

@db_session
def generate_offline_transaction():
    TransactionRequest(
        uuid=str(uuid.uuid1()),
        user=User.get(id=1),
        type='collect_cash',
        time=datetime.now(),
        success=False,
        offline=True
    )
    
@db_session
def generate_addon():
    user = User.get(id=2)
    offer = CreateOfferService.add_from_data_and_user({
        'name': 'TEST_OFFER',
        'code': 'TEST_OFFER_CODE',
        'family': 'Home',
        'type': 'Lump Sum',
        'can_be_approved_and_registered': True,
        'in_use_for_new_leads': True,
        'base_price_amount_lump_sum': 1,
    }, user)
    village = Village.select().first()
    statuses = LeadStatusService.get_allowed_statuses_for_new_lead()
    lead = AddLeadService.add_lead({
        'name': "Test",
        'surname': "Surname",
        'offer': offer.id,
        'l0_entity_id': village.id,
        'gender': 'male',
        'generator': LeadGenerator.select().first().id,
        'status': statuses.first().id,
        'preferred_phone_number': '+2341234123456'
    }, user)
    aoffer = AddonOfferService.create(user, "OFFER MOCK", "OFFERMOCK", "200", AddOnCategory.get(name="Product"), AddOnType.lump_sum, available=True, pre_sales=True)
    AddonService.create(
        contract=None,
        offer_version=aoffer.last_version,
        quantity_sold=1,
        sale_made_by=user,
        mobile_uuid=str(uuid.uuid1()),
        lead=lead
    )
        


def create_fake_phone_number():
    return '+' + SettingsService.get_setting('PhoneExtension') + str(randint(100000000, 999999999))


@db_session
def create_system_user():
    headquarters_shop = db.Hub.get(name="Shop5")
    user = EditUserService.add_user(
        None,
        'system', 'User', config.SYSTEM_EMAIL,'test1234',
        get_role_from_name('SuperAdmin'),
        headquarters_shop
    )
    user.roles_in_entities.create(sync_entity=True)
