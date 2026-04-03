from decimal import Decimal
from datetime import datetime
from payg_loan_system.contracts.models.addons_model import AddOnType
from payg_loan_system.contracts.models.contract_status import ContractStatus
from pony import orm
from payg_loan_system.offers.models import OfferType
from payg_loan_system.contracts.models.contract_event_model import ContractEventType
from payg_loan_system.contracts.models.repayment_model import ContractRepayment
from shared.helpers.date_helper import timedelta_to_hours, days_until_date


class ContractInterfaces:

    def get_hours_before_payment_due(self):
        if self.offer.type in [OfferType.usage_based, OfferType.lump_sum]:
            return None
        due_time = self.next_repayment_due_time if self.next_repayment_due_time else datetime.now()
        time_before_payment = due_time - datetime.now()
        time_before_payment_hours = timedelta_to_hours(time_before_payment)
        return time_before_payment_hours if time_before_payment_hours < 0 else Decimal(0)

    def update_device_status(self, credit_value=None):
        device = self.linked_device
        due_date = self.next_repayment_due_time
        if device and due_date:
            device.ActiveUntil = due_date
        if device and credit_value:
            if device.credit_balance is None:
                device.credit_balance = Decimal(0)
            device.credit_balance += credit_value

    # Key Metrics - Addons

    def get_total_value_with_addons(self, time=None, include_pending=False, cached=False):
        if self.get_total_value(time) is None:
            return None
        return self.get_total_value(time, cached=cached) + self.get_total_value_of_lumpsum_addons(time, include_pending=include_pending, cached=cached)

    def get_addons_in_period(self, time, from_time=None):
        if not from_time:
            from_time = datetime.min
        return orm.select(addon for addon in self.add_ons if addon.time_paid >= time and addon.time_paid >= from_time)

    def get_total_value_of_lumpsum_addons(self, time=None, from_time=None, include_pending=False, only_pending=False, cached=False):
        if cached and not time and not from_time and not include_pending and not only_pending and self.cached_lump_sum_addon_amount is not None:
            return self.cached_lump_sum_addon_amount
        if not time:
            addons = self.add_ons
        else:
            addons = self.get_addons_in_period(time)
        addons = addons.filter(
            lambda addon: addon.offer_version.offer.type == AddOnType.lump_sum and (
                not addon.cancelled or addon.cancelled_by_contract
            ) and not addon.offer_version.offer.purchasing_addon
        )
        if not include_pending:
            addons = addons.filter(lambda addon: addon.paid)
        if only_pending:
            addons = addons.filter(lambda addon: not addon.paid)
        value = orm.sum(addon.total_amount for addon in addons)
        return value or Decimal(0)

    def get_value_of_lumpsum_addons_discounts(self, time=None):
        if not time:
            addons = self.add_ons
        else:
            addons = self.get_addons_in_period(time)
        value = orm.sum(addon.discounted_amount for addon in addons if
                       addon.paid and addon.offer_version.offer.type == AddOnType.lump_sum)
        return value or Decimal(0)

    def get_value_of_lumpsum_addons_paid_without_discount(self, cached=False):
        return self.get_total_value_of_lumpsum_addons(cached=cached)-self.get_value_of_lumpsum_addons_discounts()

    def get_remaining_due_on_lumpsum_addons(self, time=None, from_time=None):
        return self.get_total_value_of_lumpsum_addons(time, from_time, include_pending=True, only_pending=True)

    # Other Metrics - Progression

    def offer_at(self, time=None):
        if time:
            changes = self.contract_events.filter(lambda e: e.type == ContractEventType.offer_change)
            last_change = changes.filter(lambda e: e.time <= time).order_by(lambda e: orm.desc(e.time)).first()
            if last_change:
                return last_change.new_offer
            next_change = changes.filter(lambda e: e.time > time).order_by(lambda e: e.time).first()
            if next_change:
                return next_change.old_offer
        return self.offer

    def get_days_until_next_payment(self, time=None, next_due_time=None):
        if self.usage_based:
            return None
        if self.end_time and (not time or time >= self.end_time):
            if self.status == ContractStatus.completed:
                return None # completed contracts don't have a repayment due time but defaulted do
            time = self.end_time if time else None # but defaulted contracts do, at the end_time maximum
        next_due_time = self.get_repayment_due_time(time) if not next_due_time else next_due_time
        return days_until_date(next_due_time, time)

    def get_repayment_due_time(self, time):
        if not time:
            return self.next_repayment_due_time
        last_repay = self.get_last_repayment_at_time(time)
        return last_repay.next_repayment_due_time if last_repay else self.next_repayment_due_time

    def get_days_since_contract_start(self, time=None):
        return -days_until_date(self.start_time, time)

    def get_par_status_group(self, time=None, next_due_time=None):
        if self.end_time and (not time or time >= self.end_time):
            if self.status == ContractStatus.completed:
                return 'Completed'
            if self.status == ContractStatus.defaulted:
                return 'Defaulted'
        days_until_next_payment = self.get_days_until_next_payment(time, next_due_time=next_due_time)
        if not days_until_next_payment:
            return ''
        days_until_next_payment = round(days_until_next_payment)
        if days_until_next_payment < -90:
            return 'PAR90+'
        if days_until_next_payment < -30:
            return 'PAR31-90'
        if days_until_next_payment < -7:
            return 'PAR8-30'
        if days_until_next_payment < 0:
            return 'PAR0-7'
        return 'On Time'

    def get_last_repayment_at_time(self, time=None):
        if not time:
            time = datetime.now()
        repayments = orm.select(rp for rp in ContractRepayment if rp.contract == self and rp.time <= time)
        return repayments.order_by(lambda rp: orm.desc(rp.time)).first()
