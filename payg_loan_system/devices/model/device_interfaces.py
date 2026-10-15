from datetime import datetime
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from shared.helpers.date_helper import timedelta_to_hours
from shared.model.interface import ModelInterface
from constants import NON_PAYG_TYPE
from payg_loan_system.offers.models import OfferType


class BaseDeviceClass(ModelInterface):

    def get_offer(self):
        return self.contract.offer if self.contract else None

    def get_offer_code(self):
        offer = self.get_offer()
        if offer is None:
            return '-'
        else:
            return offer.code

    def clear(self):
        self.RegistrationTime = None
        self.ActiveUntil = None
        self.contract = None
        # We don't clear the mode on purpose

    def can_use_offer(self, new_offer):
        required_type = new_offer.get_required_device_type()
        if required_type is None:
            return True
        if required_type == self.type:
            return True
        return False

    def is_compatible_with_offer(self, new_offer):
        if self.is_nonpayg():
            return True
        if not self.allowed_units:
            # If no allowed units specified, check if it's a usage based offer
            if new_offer.type == OfferType.usage_based:
                return False
            return True
        allowed_units_clean = [unit.lower() for unit in self.allowed_units]
        # If device accepts "ANY" unit, any unit is acceptable
        if 'any' in allowed_units_clean:
            return True
        if new_offer.type == OfferType.usage_based and (not allowed_units_clean or
                                                        new_offer.credit_unit.lower() not in allowed_units_clean):
            return False
        return True

    def get_allowed_units(self):
        if self.is_nonpayg():
            if self.contract and self.contract.offer:
                if self.contract.offer.type == OfferType.usage_based:
                    return 'any except time'
                else:
                    return 'days'
        else:
            return self.allowed_units

    def get_remaining_activation_time_in_hours(self):
        if self.ActiveUntil is None:  # This happens after change of device for example
            if self.contract.next_repayment_due_time:
                self.ActiveUntil = self.contract.next_repayment_due_time
            else:
                return 0
        time_remaining = self.ActiveUntil - datetime.now()
        return max(round(timedelta_to_hours(time_remaining)), 0)

    def can_auto_activate(self):
        return DeviceAPIService.device_can_auto_activate(self)

    def is_nonpayg(self):
        return self.type == NON_PAYG_TYPE
