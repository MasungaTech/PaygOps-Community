from datetime import datetime
from decimal import Decimal
from pony.orm import PrimaryKey, Required, Optional, desc
from core_system.core_entities import db


class ActivationRequest(db.Entity):
    id = PrimaryKey(int, auto=True)
    RequestCode = Required(str)
    ReceptionTime = Required(datetime)
    Device = Required('Device', column="device")
    client = Required('Client', column='entrepreneur')
    TimeActivatedInHours = Optional(int)
    CreditsAdded = Optional(int)
    DebitMade = Required(Decimal, default=0)

    @staticmethod
    def sort(resultset, string, field_name="reception_time", order="desc"):
        try:
            field_name, order = string.split(":")
        except ValueError as error:
            print("Error {}".format(error))
        finally:
            return ActivationRequest._set_order(resultset, field_name.lower(), order)

    @staticmethod
    def _set_order(resultset, field_name, order):
        if order.lower() == "desc":
            return resultset.order_by(lambda p: desc(p.ReceptionTime))
        return resultset.order_by(lambda p: p.ReceptionTime)


class MentorRequest(db.Entity):
    id = PrimaryKey(int, auto=True)
    ReceptionTime = Required(datetime)
    Type = Required(str)
    RequestCode = Optional(str)
    ActivationTimeAddedInDays = Optional(int)
    client = Optional("Client", column='entrepreneur')
    Device = Optional('Device', column="device")
    CreditsAdded = Optional(int)
    AdditionalData = Optional(str)
    user = Optional('User', column="user")

    payment_reference = Optional(str, column='mpesa_reference')

    @staticmethod
    def sort(resultset, string, field_name="reception_time", order="desc"):
        try:
            field_name, order = string.split(":")
        except ValueError as error:
            print("Error {}".format(error))

        return MentorRequest._set_order(resultset, field_name.lower(), order)

    @staticmethod
    def _set_order(resultset, field_name, order):
        if order.lower() == "desc":
            return resultset.order_by(lambda p: desc(p.ReceptionTime))
        return resultset.order_by(lambda p: p.ReceptionTime)
