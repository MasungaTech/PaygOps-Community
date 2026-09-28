from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import json
import math
import config

import dateutil
from shared.api_helpers.client_helpers.json_serialization_helpers import deserialize_json_data
from payg_loan_system.contracts.models.repayment_discount_types import ContractRepaymentDiscountTypes
from pony import orm
from core_system.core_entities import db
from payg_loan_system.contracts.models.contract_status import ContractStatus
from payg_loan_system.contracts.models.contract_event_model import ContractEventType
from payg_loan_system.offers.models import OfferType
from payg_loan_system.contracts.models.addons_model import AddOnType
from shared.helpers.date_helper import timedelta_to_hours
from shared.logger.loggers import LogAPI
from shared.services.settings_service import SettingsService

log_api = LogAPI()

class ExpectedRepaymentTable:

    def __init__(self, maximum: Decimal):
        self.points = []
        self.total = Decimal(0)
        self.validity = datetime.min
        self.maximum = maximum

    @property
    def completed(self):
        return self.maximum and self.maximum == self.total

    def add_point(self, time: datetime, amount: Decimal, type: str = 'Contract Payment') -> None:
        if self.completed and amount > 0:
            return
        if self.maximum:
            amount = min(amount, self.maximum-self.total)
        self.total += amount
        self.points.append((time, amount, self.total, type, self.maximum))

    def finish(self, include_date_until, return_table):
        if return_table:
            return self
        if include_date_until:
            return self.total, (self.validity if not self.completed else datetime.max)
        return self.total


class IndividualContractMetricMixin:

    def get_timeliness_ratio(self, time=None, use_cache=False, cached=False, cumulative_days_in_arrears=None):
        if cached and not time and self.cached_timeliness_ratio is not None:
            return self.cached_timeliness_ratio
        if self.usage_based or self.lump_sum:
            return None
        if not time:
            now = self._get_contract_time_of_calculation()
        else:
            now = time
        if not cumulative_days_in_arrears:
            cumulative_days_in_arrears = self.get_cumulative_days_in_arrears(time=time, cached=use_cache)
        days_since_installation = timedelta_to_hours(now - self.start_time)/24
        days_not_late = days_since_installation-cumulative_days_in_arrears

        # Keep metric stable around day boundaries: tiny fractional-day differences (seconds)
        # should not swing the ratio by truncating to the previous centi-day.
        days_not_late = Decimal(days_not_late).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        days_since_installation = Decimal(days_since_installation).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        if days_since_installation == 0 or days_not_late < 0:
            return 0
        return days_not_late/days_since_installation

    # Cumulative days in arrear (late)
    # We only consider days late, not negative, as the days in advance carry into the current timeline,
    # while days late are lost (unless include_negative=True)
    def _get_cumulative_days_in_arrear(self, include_negative=False, time=None, use_cache=False):
        if self.usage_based or self.lump_sum:
            return None
        cumulative_days_in_arrear = self.get_cumulative_days_in_arrear_until_last_payment(time=time, cached=use_cache)
        days_late_on_next_payment = self.get_days_in_arrears_since_last_payment(time=time) or 0
        if not include_negative:
            days_late_on_next_payment = max(days_late_on_next_payment, 0)
        return cumulative_days_in_arrear + days_late_on_next_payment

    def get_cumulative_days_in_arrear_until_last_payment(self, time=None, cached=False):
        if cached and not time and self.cached_cumulative_days_in_arrears_until_last_payment is not None:
            return self.cached_cumulative_days_in_arrears_until_last_payment
        if self.usage_based or self.lump_sum:
            return None
        repayments = IndividualContractMetricMixin._older_repayments(self, time)
        cumulative_days_in_arrear = orm.sum(repayment.hours_late/24 for repayment in repayments
                                             if repayment.hours_late > 0 and not repayment.converse)
        return cumulative_days_in_arrear

    # Cumulative days in arrear (late)
    def get_cumulative_days_in_arrears(self, time=None, use_cache=False, cached=False):
        if cached and not time and self.cached_cumulative_days_late is not None:
            return self.cached_cumulative_days_late
        if self.usage_based or self.lump_sum:
            return None
        return self._get_cumulative_days_in_arrear(time=time, use_cache=use_cache)

    # Cumulative days in arrear (late)
    def get_net_cumulative_days_in_arrears(self):
        return self._get_cumulative_days_in_arrear(include_negative=True)

    def get_net_cumulative_amount_in_arrears(self, cached=False):
        return self.get_cumulative_amount_in_arrears(include_negative=True, cached=cached)

    # Cumulative amount in arrears excluding time in advance.
    # We only consider days late, not negative, as the days in advance carry into the current timeline,
    # while days late are lost (unless include_negative=True)
    def get_cumulative_amount_in_arrears(self, time=None, include_negative=False, from_time=None, cached=False, repaid=None, expected=None):
        if self.usage_based:
            return None
        if not expected:
            expected = self.get_expected_amount_repaid(time=time, from_time=from_time, cached=cached)
        if not repaid:
            repaid = self.get_cumulative_amount_repaid(time=time, from_time=from_time, cached=cached)
        arrears = expected - repaid
        if not include_negative:
            return max(arrears - min(self.get_amount_in_arrears_since_last_payment(time=time, from_time=time, cached=cached), Decimal(0)), Decimal(0))
        return max(arrears, Decimal(0))

    # Cumulative hours in arrear since last payment (late)
    # We consider that payment over the principal period (e.g. 7 days) are negative arrears as they are prepayments
    def get_days_in_arrears_since_last_payment(self, time=None, from_time=None):
        paused_duration = self.paused_duration()
        days_until_next_payment = self.get_days_until_next_payment(time=time)
        if paused_duration and days_until_next_payment:
            paused_duration_in_days = timedelta_to_hours(paused_duration)/Decimal(24)
            days_until_next_payment -= paused_duration_in_days
        days_late_on_next_payment = -days_until_next_payment if days_until_next_payment is not None else None
        if days_late_on_next_payment is not None and days_late_on_next_payment < -self.offer.base_price_credit:
            days_late_on_next_payment += self.offer.base_price_credit
        return days_late_on_next_payment

    def get_amount_in_arrears_since_last_payment(self, time=None, from_time=None, cached=False):
        if self.usage_based:
            return None
        last_repayment = self._get_last_repayment(time)
        # We use the last repayment as starting time if none is specified, unless its the downpayment
        if not from_time and last_repayment and last_repayment.discount_type != 'Downpayment':
            from_time = last_repayment.time
        expected = self.get_expected_amount_repaid(time=time, from_time=from_time, cached=cached)
        last_undo_completion = self.contract_events.filter(
            lambda ce: ce.type == ContractEventType.undo_completion
        ).order_by(lambda ce: orm.desc(ce.time)).first()
        if last_repayment and (not last_undo_completion or (from_time and last_undo_completion.time <= from_time)):
            repaid = last_repayment.amount
        else:
            repaid = Decimal(0)
        # If there is no last_repayment and no from_time it with it was a 0 downpayment
        # Or if there is a last_repayment that is a Downpayment
        if (not last_repayment and not from_time) or last_repayment and last_repayment.discount_type == 'Downpayment':
            repaid = repaid + self.loan_addons_downpayments
        return expected - repaid

    def _get_last_repayment(self, time):
        last_repayment = IndividualContractMetricMixin._older_repayments(self, time=time).\
            filter(lambda r: r.amount != 0 and not r.converse).\
            order_by(lambda r: orm.desc(r.time)).first()
        return last_repayment

    def get_cumulative_amount_repaid_without_deposit(self, time=None, from_time=None):
        return self.get_cumulative_amount_repaid(time, from_time, no_downpayment=True)

    def get_cumulative_amount_repaid(self, time=None, from_time=None, cached=False, no_downpayment=False):
        if not no_downpayment and cached and not time and not from_time and self.cached_cumulative_amount_repaid is not None:
            return self.cached_cumulative_amount_repaid
        repayments = IndividualContractMetricMixin._older_repayments(self, time, from_time)
        if no_downpayment:
            repayments = repayments.filter(lambda r: r.discount_type != ContractRepaymentDiscountTypes.downpayment)
        amount = round(orm.sum(repayment.amount for repayment in repayments), 2)
        if no_downpayment or (from_time and from_time > self.start_time):
            return amount
        return amount + self.loan_addons_downpayments_paid

    def get_cumulative_amount_repaid_with_addons(self, time=None, from_time=None):
        return self.get_cumulative_amount_repaid(time, from_time)+self.get_total_value_of_lumpsum_addons(time, from_time, include_pending=False)

    def get_total_loan_addons_value(self, time=None, cached=False, add_on_id=None, excluded_addon_ids=[]):
        if time:
            addons = orm.select(a for a in self.add_ons if a.time_approved <= time and not a.excluded_effects_at(time) and not a.offer_version.offer.purchasing_addon)

        else:
            addons = orm.select(a for a in self.add_ons if not a.excluded_effects and not a.offer_version.offer.purchasing_addon)
        if add_on_id:
            addons = addons.filter(lambda a: a.id < add_on_id)
        loan_addons_value = orm.sum(a.total_amount for a in addons \
                       if a.loan \
                        and a.id not in excluded_addon_ids
                    ) or 0
        return loan_addons_value
    
    def get_total_extended(self, time=None, cached=False):
        if cached and not time and self.cached_loan_extension_addon_amount is not None:
            return self.cached_loan_extension_addon_amount
        total = self.get_total_loan_addons_value(time, cached)
        return total - self.loan_addons_downpayments

    def get_total_extended_days(self, time=None):
        time = time or datetime.max
        return orm.sum(a.extension_days for a in self.add_ons if (
                not a.excluded_effects_at(time)
                and a.onloan and a.time_approved <= time
        )) or 0

    def get_total_value(self, time=None, cached=False, add_on_id=None, excluded_addon_ids=[]):
        if cached and not time and self.cached_total_value is not None:
            return self.cached_total_value
        if not self.can_be_completed:
            return None
        return self.offer_at(time).get_total_value_with_deposit() + self.get_total_loan_addons_value(time, add_on_id=add_on_id, excluded_addon_ids=excluded_addon_ids)
    
    def queryable_total_value(self):
        return (
            # Base total offer value
            (self.offer.time_to_ownership_in_days-self.offer.free_credit_at_start)*self.offer.base_price_amount/self.offer.base_price_credit+self.offer.registration_fee
            # + total amount added with loan addons not cancelled
            +sum(a.total_amount for a in self.add_ons if a.loan and not a.excluded_effects and not a.offer_version.offer.purchasing_addon)
        )
    
    def queryable_balance_lump_sum(self):
        return sum(a.total_amount-a.already_paid for a in self.add_ons if a.offer_version.offer.type == AddOnType.lump_sum and not a.cancelled)

    def queryable_balance(self):
        return (
            self.queryable_total_value()
            # - paid in repayments
            -sum(r.amount for r in self.repayments)
            # - paid in downpayments of addons
            -self.loan_addons_downpayments_paid
        )
    
    def get_yearly_value(self, time=None):
        return self.offer_at(time).get_yearly_value()

    def get_total_value_without_deposit(self):
        return self.get_total_value()-self.get_total_downpayment() if self.can_be_completed else None

    def get_total_days_to_ownership(self, cached=False):
        if cached and self.cached_total_days_to_ownership is not None:
            return self.cached_total_days_to_ownership
        return self.offer.get_days_to_ownership()+self.get_total_extended_days() \
            if self.can_be_completed else None

    def get_percentage_repaid(self, cached=False, use_cache=False):
        if not self.can_be_completed:
            return None
        if cached and self.cached_percentage_paid is not None:
            return self.cached_percentage_paid
        total_repaid = self.get_cumulative_amount_repaid(cached=use_cache)
        total_value = self.get_total_value(cached=use_cache)
        if total_value == 0:
            return Decimal(1)
        if total_value < total_repaid:
            return Decimal(1) # For overpaid contracts, we return 100%
        return total_repaid/total_value

    def get_days_paid(self):
        if not self.loan:
            return None
        return self.get_days_to_pay()-self.get_remaining_days_to_pay()

    def get_days_to_pay(self, time=None):
        if not self.loan:
            return None
        return self.offer_at(time).time_to_ownership_in_days + self.get_total_extended_days(time=time)

    def get_remaining_days_to_pay(self):
        if not self.can_be_completed:
            return None
        return self.get_outstanding_balance()/self.get_base_price_per_credit()

    def get_weeks_progression_dict(self):
        if not self.can_be_completed or not self.loan:
            return None
        days_paid = round(self.get_days_paid())
        days_to_pay = round(self.get_days_to_pay())
        remaining_days_to_pay = round(self.get_remaining_days_to_pay())
        weeks_paid = int(days_paid/7)
        days_paid = int(days_paid) - (weeks_paid * 7)
        weeks_to_pay = int(round(days_to_pay/7))
        remaining_weeks_to_pay = int(round(remaining_days_to_pay/7))
        return {
            'weeks_paid': weeks_paid,
            'days_paid': days_paid,
            'weeks_to_pay': weeks_to_pay,
            'days_to_pay': days_to_pay,
            'remaining_weeks_to_pay': remaining_weeks_to_pay,
            'remaining_days_to_pay': remaining_days_to_pay
        }

    # Number of time the lease entered arrears
    def get_number_of_times_lease_entered_arrears(self):
        if self.usage_based:
            return None
        number_of_times_in_arrears = orm.count(repayment for repayment in self.repayments
                                               if repayment.hours_late > 0 and repayment.amount and not repayment.converse)
        currently_in_arrears = int((self.get_days_in_arrears_since_last_payment() or 0) > 0)
        return number_of_times_in_arrears + currently_in_arrears

    # Date last current
    def get_date_last_current(self):
        if self.usage_based:
            return None
        if self.status == ContractStatus.completed:
            return self.end_time
        if self.next_repayment_due_time < datetime.now():
            return self.next_repayment_due_time
        return datetime.now()

    # Date last in arrear
    def get_date_last_in_arrears(self):
        if self.usage_based:
            return None
        if self.next_repayment_due_time < datetime.now():
            if self.status == ContractStatus.active:
                return datetime.now()
            return self.end_time
        late_payments = orm.select(repayment for repayment in self.repayments if repayment.hours_late > 0)
        last_late_payment = late_payments.order_by(orm.desc(db.ContractRepayment.time)).first()
        return last_late_payment.time if last_late_payment else None

    # Outstanding Balance
    def get_outstanding_balance(self, time=None, cached=False, add_on_id=None, excluded_addon_ids=[]):
        return self.get_total_value(time, cached=cached, add_on_id=add_on_id, excluded_addon_ids=excluded_addon_ids) - self.get_cumulative_amount_repaid(time, cached=cached) \
            if self.can_be_completed else None

    # Outstanding Balance with unpaid addons
    def get_outstanding_balance_with_addons(cls, time=None):
        return (cls.get_total_value(time) - cls.get_cumulative_amount_repaid(time)) + cls.get_remaining_due_on_lumpsum_addons(time) \
            if cls.can_be_completed else None

    # Expected Outstanding Balance
    def get_expected_oustanding_balance(self, cached=False):
        return self.get_total_value() - self.get_expected_amount_repaid(cached=cached) \
            if self.can_be_completed else None

    # Number of repayments with balance
    def get_number_of_non_null_repayments(self):
        return orm.count(repayment for repayment in self.repayments if repayment.amount and not repayment.converse)

    # Date of lease maturity at origination
    def get_date_of_maturity_without_lateness(self, time=None):
        if not self.loan:
            return None
        days_to_pay = self.get_days_to_pay(time=time)
        return self.start_time + timedelta(days=float(days_to_pay if days_to_pay < 99999 else 99999))

    # Current date of lease maturity
    def get_date_of_maturity(self, time=None):
        if not self.loan:
            return None
        if self.status == ContractStatus.completed:
            return self.end_time
        delayed = self.get_total_days_delays_given(time=time)
        if self.offer_at(time).forgive_lateness:
            delayed += self._get_cumulative_days_in_arrear(time=time)
        return self.get_date_of_maturity_without_lateness(time) + timedelta(days=float(delayed))

    # Default Amount
    def get_default_amount(self):
        if self.status != ContractStatus.defaulted:
            return None
        return self.get_outstanding_balance()

    # GOGLA Default date
    def get_gogla_default_date(self):
        if self.usage_based:
            return None
        base_gogla_date = self.next_repayment_due_time + timedelta(days=90)
        if self.status == ContractStatus.defaulted and self.end_time < base_gogla_date:
            return self.end_time
        return base_gogla_date if base_gogla_date < datetime.now() else None

    # Get total discounted
    def get_amount_discounted(self, time=None, from_time=None, cached=False):
        if cached and not time and not from_time and self.cached_cumulative_amount_discounted is not None:
            return self.cached_cumulative_amount_discounted
        repayments = IndividualContractMetricMixin._older_repayments(self, time, from_time=from_time)
        return round(orm.sum(repayment.amount_discounted for repayment in repayments), 2)

    # Get total paid without discount
    def get_amount_paid_without_discount(self, cached=False):
        return self.get_cumulative_amount_repaid(cached=cached)-self.get_amount_discounted(cached=cached)

    def get_total_number_installments(self, time=None):
        if self.offer.type != OfferType.loan or self.reference_price == 0:
            return 0
        return (self.get_total_value_without_deposit()/self.reference_price)

    def get_number_installments(self, time=None, add_on_id=None, excluded_addon_ids=[]):
        if self.offer.type != OfferType.loan:
            return 0
        reference_price = self.reference_price_at(time=time, add_on_id=add_on_id, excluded_addon_ids=excluded_addon_ids)
        if reference_price:
            return self.get_outstanding_balance(time=time, add_on_id=add_on_id, excluded_addon_ids=excluded_addon_ids) / reference_price
        return 1

    def get_expected_payments_table(self, min_time=None, cached=False, parsed=True):
        
        end_time = datetime.max
        if not self.can_be_completed:
            end_time = self.end_time or min_time or self.offer.add_credit(datetime.now(), self.offer.base_price_credit) #must be current offer
        
        # We check if we can use the cache (in some cases before writing to DB the type is wrong so we need to check)
        if (not min_time or end_time > min_time) and cached and self.cached_expected_payments_table is not None and isinstance(self.cached_expected_payments_table, (str, bytes, bytearray)):
            raw = json.loads(self.cached_expected_payments_table)
            if not parsed:
                return raw
            for row in raw:
                row[0] = dateutil.parser.parse(row[0])
            return raw
        if self.usage_based:
            return None

        if self.get_total_number_installments() > config.MAX_INSTALLMENTS_PLANNING:
            return []

        total_delayed = timedelta(days=float(self.get_total_days_delays_given()))
        current_time = self.start_time + min(timedelta(0), total_delayed) if datetime.min - self.start_time < total_delayed else datetime.min
        log_api.check_and_warn(current_time <= end_time, "Wrong time interval of calculation")

        # this will get a list of tuples (time, price) / (time, delay) for each of the price changes and the delays, ordered by time asc
        prices_data = []
        for c in self._get_reference_price_changes(end_time, current_time):
            prices_data += [(c.time, self.reference_price_at(c.time) if c.type != ContractEventType.default else 0)]
        delays_data = [(r.time, r.delay_given_in_hours) for r in self.repayments.filter(
            lambda r: r.delay_given_in_hours != 0 and r.time <= end_time
        ).order_by(1)]

        expected_paid_changes_data = [(e.time, e.added_amount) for e in self.contract_events.filter(
            lambda e: e.type == ContractEventType.expected_paid_change and e.time <= end_time
        ).order_by(1)]

        table = ExpectedRepaymentTable(self.get_total_value(self.start_time))
        offer = self.offer_at(current_time) #from now on always the offer at current time
        downpayment = self.lead.offer.registration_fee + self.lead.loan_addons_downpayments
        table.add_point(current_time, downpayment, ContractRepaymentDiscountTypes.downpayment)
        current_time = offer.add_credit(current_time, offer.free_credit_at_start)
        table.validity = current_time
        price = self.reference_price_at(current_time)

        while expected_paid_changes_data and expected_paid_changes_data[0][0] < current_time:
            change_data = expected_paid_changes_data.pop(0)
            table.add_point(change_data[0], change_data[1], ContractEventType.expected_paid_change)

        skip_next_point = False

        max_rounding_discount = SettingsService.get_setting('MaxRoundingDiscount')

        while current_time < end_time:

            # we loop over all the price changes until current_time and stick to the last one
            while prices_data and prices_data[0][0] <= current_time:
                price = prices_data.pop(0)[1] # we get the first one in the list and remove it so we dont use it again
                table.maximum = self.get_total_value(current_time)
                offer = self.offer_at(current_time)

            # if any of the events that pauses (or finish) the contract
            if (price == 0 or table.completed) and not skip_next_point:
                #if the contract resumes later (i.e there are still events in the future)
                if prices_data or delays_data or expected_paid_changes_data:
                    current_time = min(
                        prices_data[0][0] if prices_data else datetime.max, 
                        delays_data[0][0] if delays_data else datetime.max,
                        expected_paid_changes_data[0][0] if expected_paid_changes_data else datetime.max
                    ) 
                    table.validity = current_time
                    skip_next_point = True
                    continue # We jump in time to the next event
                # else (don't resumes) return either expected till now (if defaulted) or maximum value, if completed
                return table.points

            # We add a new point
            if not skip_next_point:
                # We use this trick to avoid a very small last payment
                if table.maximum and table.total and price:
                    left_to_pay_after = table.maximum-(table.total+price)
                    if left_to_pay_after < max_rounding_discount:
                        price = price + left_to_pay_after

                table.add_point(current_time, price)
                # Prevent datetime overflow when adding credit very close to datetime.max
                days_credit = float(offer.base_price_credit)
                if current_time >= datetime.max - timedelta(days=days_credit):
                    # We cannot represent a later date; the schedule is complete within datetime limits
                    break
                current_time = offer.add_credit(current_time, offer.base_price_credit)

            # we loop over all the delays until current_time and sum the hours
            total_delayed = 0
            while delays_data and delays_data[0][0] <= current_time:
                total_delayed += delays_data.pop(0)[1] # we get the first one in the list, add it to the total and remove it so we dont use it again
            current_time += timedelta(hours=float(total_delayed))
            table.validity = current_time
            
            # We loop over all the expected payment changes
            while expected_paid_changes_data and expected_paid_changes_data[0][0] <= current_time:
                change_data = expected_paid_changes_data.pop(0)
                table.add_point(change_data[0], change_data[1], ContractEventType.expected_paid_change)

            skip_next_point = False

        return table.points

    def get_expected_number_of_repayments(self, cached=False):
        if self.usage_based or self.time_based:
            return None
        if self.lump_sum:
            return 1
        return len(self.get_expected_payments_table(cached=cached, parsed=False))
        

    def get_expected_amount_repaid(self, time=None, from_time=None, cached=False, include_date_until=False):
        if cached and not time and not from_time and self.cached_expected_amount_repaid is not None:
            return self.cached_expected_amount_repaid
        if self.usage_based:
            if include_date_until:
                return None, datetime.max
            return None
        if self.lump_sum:
            if include_date_until:
                return self.get_total_value(), datetime.max
            return self.get_total_value()
        if from_time:
            from_time=max(from_time, self.start_time)
            if from_time == self.start_time:
                return self.get_expected_amount_repaid(time, cached=cached)
            return self.get_expected_amount_repaid(time, cached=cached)-self.get_expected_amount_repaid(from_time, cached=cached)

        if not time:
            time = datetime.now()
        table = self.get_expected_payments_table(min_time=time, cached=cached)
        total = 0
        for row in table:
            validity = row[0]
            if validity > time:
                return (Decimal(str(total)), validity) if include_date_until else Decimal(str(total))
            total = row[2]
        return (Decimal(str(total)), datetime.max) if include_date_until else Decimal(str(total))

        
    def _get_reference_price_changes(self, time, from_time):
        event_types = [
            ContractEventType.offer_change,
            ContractEventType.reference_pricing_change,
            ContractEventType.duration_change,
            ContractEventType.default,
            ContractEventType.undo_default,
            ContractEventType.undo_completion,
        ]
        return self.contract_events.filter(
            lambda e: e.type in event_types and time >= e.time and e.time >= from_time
        ).order_by(db.ContractEvent.time)

    def get_delays_given_in_days(self, time, from_time):
        if not from_time:
            from_time = datetime.min
        repayments = IndividualContractMetricMixin._older_repayments(self, time=time)
        delays_in_hours = 0
        delays = orm.select(repayment for repayment in repayments if repayment.delay_given_in_hours != 0)
        for delay in delays:
            delayed_time = delay.time + timedelta(hours=int(delay.delay_given_in_hours))
            # We only count the delays that ended after the beginning of the period
            if delayed_time > from_time:
                if delay.time > from_time:
                    # delay started during the period
                    ref_time = delay.time
                else:
                    # delay started before the period
                    ref_time = from_time
                # We make the difference to exclude the hours outside of the period
                delays_in_hours += min(timedelta_to_hours(min(time, delayed_time) - ref_time), delay.delay_given_in_hours)
        return Decimal(delays_in_hours/24)

    def get_total_days_delays_given(self, time=None):
        hours = orm.sum(repayment.delay_given_in_hours for repayment in self.repayments if repayment.delay_given_in_hours != 0 and repayment.time <= (time or datetime.max))
        if hours:
            return Decimal(hours/24)
        return Decimal(0)

    def get_total_discounted(self, time=None):
        return orm.sum(repayment.amount_discounted for repayment in self.repayments if repayment.amount_discounted != 0 and repayment.time <= (time or datetime.max))

    def get_total_value_without_discounts(self, time=None, cached=True):
        total_value = self.get_total_value(time=time, cached=cached)
        if total_value: return total_value-self.get_total_discounted(time=time)
        else: return None

    # get_expected_percentage_repaid
    def get_expected_percentage_repaid(self, cached=False):
        total_value = self.get_total_value(cached=cached)
        if total_value == 0:
            return Decimal(1)
        if not self.can_be_completed:
            return None
        return self.get_expected_amount_repaid(cached=cached) / total_value
    
    def _get_contract_time_of_calculation(self):
        if self.status in [ContractStatus.active, ContractStatus.paused, ContractStatus.late, ContractStatus.overpaid]:
            return datetime.now()
        if not self.end_time:
            raise Exception('Contract missing end-time')
        return self.end_time

    # Average Payment Frequency
    def get_average_days_between_payments(self):
        now = self._get_contract_time_of_calculation()
        days_since_registration = timedelta_to_hours(now - self.start_time)/24
        non_null_repayments = self.get_number_of_non_null_repayments()
        return days_since_registration/non_null_repayments if non_null_repayments else 0

    def get_credits_bought(self, time=None, from_time=None, cached=True):
        if self.cached_cumulative_credit_bought is not None and cached and not time and not from_time:
            return self.cached_cumulative_credit_bought
        repayments = IndividualContractMetricMixin._older_repayments(self, time=time, from_time=from_time)
        return orm.sum(r.credit_value for r in repayments if r.credit_value) or 0

    def get_average_monthly_usage(self):
        now = self.end_time if self.status != ContractStatus.active else datetime.now()
        months_since_registration = (timedelta_to_hours(now - self.start_time)/24)/30
        usage_bought = self.get_credits_bought()
        return usage_bought/months_since_registration if months_since_registration >= 1 else usage_bought

    def get_average_monthly_payments(self):
        now = self.end_time if self.status != ContractStatus.active else datetime.now()
        months_since_registration = (timedelta_to_hours(now - self.start_time)/24)/30
        amount_repaid = self.get_cumulative_amount_repaid_without_deposit()
        return amount_repaid/months_since_registration if months_since_registration >= 1 else amount_repaid

    def get_cumulative_amount_repaid_this_year(self):
        jan1st = datetime(datetime.now().year, 1, 1)
        return self.get_cumulative_amount_repaid(time=datetime.now(), from_time=jan1st)

    def get_cumulative_amount_repaid_last_month(self):
        today = datetime.today()
        first = today.replace(day=1)
        last_day_of_last_month = first - timedelta(days=1)
        first_day_of_last_month = last_day_of_last_month.replace(day=1)
        return self.get_cumulative_amount_repaid(time=last_day_of_last_month, from_time=first_day_of_last_month)

    def get_cumulative_amount_repaid_last_week(self):
        start_date = datetime.today() + timedelta(-datetime.today().weekday(), weeks=-1)
        end_date = datetime.today() + timedelta(-datetime.today().weekday() - 1)
        return self.get_cumulative_amount_repaid(time=end_date, from_time=start_date)

    def get_credits_bought_this_year(self):
        jan1st = datetime(datetime.now().year, 1, 1)
        return self.get_credits_bought(datetime.now(), jan1st)

    def get_credits_bought_last_month(self):
        today = datetime.today()
        first = today.replace(day=1)
        last_day_of_last_month = first - timedelta(days=1)
        first_day_of_last_month = last_day_of_last_month.replace(day=1)
        return self.get_credits_bought(last_day_of_last_month, first_day_of_last_month)

    def get_credits_bought_last_week(self):
        start_date = datetime.today() + timedelta(-datetime.today().weekday(), weeks=-1)
        end_date = datetime.today() + timedelta(-datetime.today().weekday() - 1)
        return self.get_credits_bought(end_date, start_date)

    @staticmethod
    def _older_repayments(contract, time=None, from_time=None):
        if not time and not from_time:
            return contract.repayments
        if not time:
            time = datetime.max
        if not from_time:
            from_time = datetime.min
        return contract.repayments.filter(lambda r: r.time < time and r.time >= from_time)

    # Remaining due if paid now (discounted)
    def get_outstanding_balance_discounted(self, cached=False):
        if self.offer.type == OfferType.time_based or self.offer.type == OfferType.usage_based:
            return None
        remaining_amount = self.get_outstanding_balance(cached=cached)
        return self.get_discounted_amount_from_amount_to_pay(remaining_amount, cached=cached)

    def get_discounted_amount_from_amount_to_pay(self, remaining_amount, cached=False):
        discount_price_1 = self.discount_price_1_at(cached=cached)
        if not (discount_price_1 and remaining_amount >= discount_price_1):
            return remaining_amount
        base_price_per_credit = self.get_base_price_per_credit(cached=cached)
        to_pay = round(remaining_amount/(base_price_per_credit/self.get_discount_1_price_per_credit(cached=cached)), 2)
        if not (discount_price_1 and to_pay >= discount_price_1):
            return discount_price_1
        discount_price_2 = self.discount_price_2_at(cached=cached)
        if not (discount_price_2 and remaining_amount >= discount_price_2):
            return to_pay
        to_pay = round(remaining_amount/(base_price_per_credit/self.get_discount_2_price_per_credit(cached=cached)), 2)
        if not (discount_price_2 and to_pay >= discount_price_2):
            return discount_price_2
        return to_pay

    def get_base_price_per_credit(self, cached=False, time=None, add_on_id=None):
        if self.offer.base_price_credit == 0:
            return Decimal(0)
        return Decimal(self.reference_price_at(cached=cached, time=time, add_on_id=add_on_id)/self.offer.base_price_credit)

    def get_discount_1_price_per_credit(self, cached=False):
        return self.discount_price_1_at(cached=cached)/self.offer.discount_price_1_credit

    def get_discount_2_price_per_credit(self, cached=False):
        return self.discount_price_2_at(cached=cached)/self.offer.discount_price_2_credit

    def get_last_non_null_repayment(self, time=None):
        non_null_repayments = orm.select(r for r in self.repayments if r.amount and not r.converse and r.time <= (time or datetime.max))
        last_non_null = non_null_repayments.order_by(lambda c: orm.desc(c.time)).first()
        return last_non_null

    @staticmethod
    def _to_days(x):
        return x/24 if x else x
