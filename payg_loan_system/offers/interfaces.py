from decimal import Decimal
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from config import OFFERS_HUMAN_READABLE_TYPES, OFFERS_HUMAN_READABLE_TYPES_SHORT, OFFERS_HUMAN_READABLE_TYPES_NEW_SHORT

class OfferInterfaces:

    def get_human_readable_type(self):
        return OFFERS_HUMAN_READABLE_TYPES.get(
            self.type,
            OFFERS_HUMAN_READABLE_TYPES[None]
        )

    def get_human_readable_type_short_new(self):
        return OFFERS_HUMAN_READABLE_TYPES_NEW_SHORT.get(
            self.type,
            OFFERS_HUMAN_READABLE_TYPES_NEW_SHORT[None]
        )

    def get_human_readable_type_short(self):
        return OFFERS_HUMAN_READABLE_TYPES_SHORT.get(
            self.type,
            OFFERS_HUMAN_READABLE_TYPES_SHORT[None]
        )

    def get_required_device_type(self):
        return self.device_type or None

    def get_human_readable_device_type(self, empty='Any'):
        dtype = self.get_required_device_type()
        type_name = DeviceAPIService.get_device_human_readable_type_name(dtype) if dtype else empty
        if self.product_sub_type:
            type_name += ' - '+self.product_sub_type.name 
        return type_name

    def discount_applies(self, discount, amount):
        discount_price = self.get_discount_amount(discount)
        return discount_price and amount >= discount_price

    def apply_discount(self, discount, amount):
        discount_rate = self.get_discount_rate(discount)
        return round(amount/discount_rate, 2)

    def get_discount_amount(self, d):
        return self.discount_price_1_amount if d == 1 else self.discount_price_2_amount

    def get_discount_credit(self, d):
        return self.discount_price_1_credit if d == 1 else self.discount_price_2_credit

    def get_discount_rate(self, d):
        return self.get_discount_1_discount_rate() if d == 1 else self.get_discount_2_discount_rate()

    def get_yearly_value(self):
        if self.is_monthly:
            value = 12*self.get_base_price_per_credit()
        else:
            value = 365*self.get_base_price_per_credit()
        return round(value, 2)

    def get_total_value_without_deposit(self):
        value = self.get_time_to_pay()*self.get_base_price_per_credit()
        return round(value, 2)

    def get_total_value_with_deposit(self):
        value = self.get_time_to_pay()*self.get_base_price_per_credit()+self.registration_fee
        return round(value, 2)

    def get_fully_discounted_loan_amount_with_deposit(self):
        value = self.get_time_to_pay()*self.get_most_discounted_price()+self.registration_fee
        return round(value, 2)

    def get_base_price_per_credit(self):
        if self.base_price_credit == 0:
            return Decimal(0)
        return Decimal(self.base_price_amount/self.base_price_credit)

    def get_discount_1_price_per_credit(self):
        return self.discount_price_1_amount/self.discount_price_1_credit

    def get_discount_2_price_per_credit(self):
        return self.discount_price_2_amount/self.discount_price_2_credit

    def get_most_discounted_price(self):
        if self.discount_price_2_amount:
            return self.get_discount_2_price_per_credit()
        elif self.discount_price_1_amount:
            return self.get_discount_1_price_per_credit()
        else:
            return self.get_base_price_per_credit()

    def get_discount_1_discount_rate(self):
        return self.get_base_price_per_credit()/self.get_discount_1_price_per_credit()

    def get_discount_2_discount_rate(self):
        return self.get_base_price_per_credit()/self.get_discount_2_price_per_credit()

    def get_ratio_of_price_with_other_offer(self, new_offer):
        old_total_value = self.get_total_value_without_deposit()
        new_total_value = new_offer.get_total_value_without_deposit()
        old_time_to_ownership = self.time_to_ownership_in_days
        new_time_to_ownership = new_offer.time_to_ownership_in_days
        return (old_total_value/new_total_value)*(new_time_to_ownership/old_time_to_ownership)

class LoanOfferInterface(OfferInterfaces):

    def get_days_to_ownership(self):
        return self.time_to_ownership_in_days

    def get_time_to_pay(self):
        return self.time_to_ownership_in_days-self.free_credit_at_start

class TimeBasedOfferInterface(OfferInterfaces):
    def get_days_to_ownership(self):
        return 0

    def get_time_to_pay(self):
        return 0


class UsageBasedOfferInterface(OfferInterfaces):
    def get_days_to_ownership(self):
        return 0

    def get_time_to_pay(self):
        return 0

    def get_yearly_value(self):
        return None


class LumpSumOfferInterface(OfferInterfaces):
    def get_days_to_ownership(self):
        return 0

    def get_time_to_pay(self):
        return 0

    def get_yearly_value(self):
        return None