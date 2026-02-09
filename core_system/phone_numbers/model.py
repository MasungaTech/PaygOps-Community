from pony.orm import PrimaryKey, Required, Optional, select, Set
from shared.model.interface import ModelInterface
from core_system.core_entities import db


class PhoneNumbers(db.Entity, ModelInterface):

    id = PrimaryKey(int, auto=True)
    number = Required(str, unique=True, index=True)
    personContactPhone = Set("Person") # reverse for contact_phone (primary)
    person = Optional("Person", column="person")
    persons = Set("Person", reverse="phoneNumbers")
    payment_wallet = Optional('PaymentWallet')
