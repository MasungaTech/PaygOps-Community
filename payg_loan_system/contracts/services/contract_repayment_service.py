from decimal import Decimal
from math import ceil
from datetime import datetime, timedelta
from payg_loan_system.contracts.models.addons_model import AddOnType
from constants import MAX_CREDIT_PER_REPAYMENT_ALLOWED
from messages_system.services.message_service import MessageService
from payg_loan_system.contracts.models.repayment_model import ContractRepayment
from payg_loan_system.contracts.models.contract_event_model import ContractEvent, ContractEventType
from payg_loan_system.contracts.models.reconciled_payment_type import ReconciledPaymentType
from payg_loan_system.contracts.models.repayment_discount_types import ContractRepaymentDiscountTypes
from payg_loan_system.contracts.models.contract_status import ContractStatus
from payg_loan_system.actions.activation import sync_activation
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from pony import orm
from pony.orm.core import select
from payg_loan_system.devices.model.device_mode import DeviceMode
from payg_loan_system.contracts.services.reconciled_payment_service import ReconciledPaymentService
from payg_loan_system.offers.models import OfferType
from shared.logger.loggers import Error, LogAPI
from shared.helpers.date_helper import DateDifferenceService, get_days_in_month, timedelta_to_hours, add_months, set_day_of_month
import config
from shared.services.settings_service import SettingsService
from shared.api_helpers.hook_helpers.process_hook import add_hook_after_commit
from core_system.core_entities import db
import time


class ContractRepaymentService:

    @classmethod
    def clear_pending_payment_if_needed(cls, contract):
        # If there were more repayments made in between and now there is too much to pay, we clear what there is
        if contract.can_be_completed and contract.pending_amount > contract.get_outstanding_balance_discounted():
            for pending in contract.pending_reconciled_payments_filtered:
                ReconciledPaymentService.revert(pending)

    @classmethod
    def repay_and_reconcile(cls, contract, payment=None, account=None, amount=0, note='', lead=None, force_time=None, origin_reconciled_payment=None):
        repayments = []
        payment = cls._try_to_match_payment(payment, account, amount)
        if not amount:
            amount = payment.remaining if payment else 0
        amount_to_repay = cls._get_amount_to_repay(contract, amount)
        payment_time = force_time or getattr(payment, 'PaymentTime', None)
        last_repayment_time = select(rp.time for rp in contract.repayments.filter(
            lambda r: r.discount_type in ['', ContractRepaymentDiscountTypes.downpayment]
        )).max()
        if payment_time and last_repayment_time and payment_time < last_repayment_time:
            #If is an old payment we use now as the repayment time for keeping the repayment order
            payment_time = None
        just_pending = not payment and not account and not amount
        creating_downpayment = False
        if not SettingsService.get_setting('EnableContractPaymentsForReversedDownpayments') and not contract.downpayment_fully_paid and amount_to_repay >= contract.offer.registration_fee:
            creating_downpayment = True
        while not repayments or (amount_to_repay and not contract.status == ContractStatus.completed) or creating_downpayment:
            if cls.check_can_create_repayment(contract, amount_to_repay, payment_time):
                now = datetime.now()
                if not just_pending and amount_to_repay != 0:
                    reconciled = ReconciledPaymentService.create_reconciliation(payment=payment, account=account, time=payment_time or now,
                                                                                amount=amount, repayment_amount=amount_to_repay-contract.pending_amount,
                                                                                note=note, lead=lead, origin_reconciled_payment=origin_reconciled_payment)
                    amount -= reconciled.amount
                repayment = cls._create_repayment_from_amount_paid(contract, amount_to_repay, payment_time or now)
                cls._reconcile_pending_reconciled_payments(contract, repayment)
                if not just_pending and amount_to_repay != 0:
                    reconciled.repayment = repayment
                    add_hook_after_commit(db, 'new_reconciliation', reconciled.get_serialized_object())
            else: # it was below minimum or paused
                if not just_pending and amount != 0:
                    ReconciledPaymentService.create_reconciliation(payment=payment, account=account, amount=amount,
                                                                   contract_pending_repayment=contract, note=note, lead=lead, origin_reconciled_payment=origin_reconciled_payment)
                break
            orm.flush()
            if repayment.total_reconciled != repayment.amount_paid:
                raise Exception("Repayment creation attempt with mismatching reconciliations")
            if repayment.orphaned_simple_payment:
                raise Exception("Repayment creation attempt with orphaned simple payment")
            repayments.append(repayment)
            amount_to_repay = cls._get_amount_to_repay(contract, amount)
            creating_downpayment = False
        return repayments

    @staticmethod
    def _try_to_match_payment(payment, account, amount):
        last_payment = account.get_last_payment() if account else None
        return last_payment if last_payment and last_payment.remaining == amount else payment

    @classmethod
    def _get_amount_to_repay(cls, contract, available_amount):
        amount_paid_previous = contract.pending_amount
        outstanding_balance = contract.get_outstanding_balance_discounted()
        amount_to_repay = amount_paid_previous + available_amount
        if cls._check_if_first_repayment_with_day_of_month(contract):
            return cls._get_amount_to_repay_until_day_of_month(contract)
        if not contract.downpayment_fully_paid and not SettingsService.get_setting('EnableContractPaymentsForReversedDownpayments'):
            return min(contract.offer.registration_fee, amount_to_repay)
        if contract.can_be_completed and amount_to_repay > outstanding_balance and outstanding_balance > 0:
            return outstanding_balance
        if contract.offer.allow_pro_rata:
            return amount_to_repay
        bundles = [contract.discount_price_2 or float('inf'),
                   contract.discount_price_1 or float('inf'),
                   contract.minimum_payment]
        for bundle in bundles:
            if bundle <= amount_to_repay:
                return bundle
        return amount_to_repay

    @classmethod
    def _check_if_first_repayment_with_day_of_month(cls, contract):
        if contract.offer.type != OfferType.time_based:
            return False
        contract_repayment_not_downpayment = [cr for cr in contract.repayments if cr.discount_type != ContractRepaymentDiscountTypes.downpayment]
        return not contract_repayment_not_downpayment and contract.offer.payment_day_of_month is not None

    @classmethod
    def _get_amount_to_repay_until_day_of_month(cls, contract):
        if contract.start_time.day > contract.offer.payment_day_of_month:
            date_to_pay_until = set_day_of_month(add_months(contract.start_time, 1), contract.offer.payment_day_of_month)
        else:
            date_to_pay_until = set_day_of_month(contract.start_time, contract.offer.payment_day_of_month)
        days_in_month = get_days_in_month(contract.start_time)
        number_of_days_to_pay = DateDifferenceService.number_of_days_in_between(contract.start_time, date_to_pay_until) - 1
        fraction_of_month_to_pay = number_of_days_to_pay/days_in_month
        # fraction_of_month_to_pay is the fraction of the month to be paid from when the contract is started until the next day of payment
        # (for monthly offers that force a day of payment)
        monthly_price = contract.reference_price/contract.offer.base_price_credit
        amount = monthly_price * Decimal(fraction_of_month_to_pay)
        # Then "contract.reference_price/contract.offer.base_price_credit" is the price (including addons increase) to pay per
        # month (we divide the reference pricing over the reference frequency that could be more than one month) and then we
        # multiply that monthly price by the fraction of the month to be paid.
        return round(amount, 2)


    @classmethod
    def _reconcile_pending_reconciled_payments(cls, contract, repayment):
        for rp in contract.pending_reconciled_payments_filtered:
            orm.flush()
            if rp.amount > repayment.amount_paid - repayment.total_reconciled:
                to_reconcile = repayment.amount_paid - repayment.total_reconciled
                remaining = rp.amount - to_reconcile
                rp.amount = to_reconcile
                rp.contract_pending_repayment = None
                rp.type = ReconciledPaymentType.repayment
                rp.repayment = repayment
                ReconciledPaymentService.create_reconciliation(payment=rp.linked_payment, account=rp.payment_account,
                                                               amount=remaining, contract_pending_repayment=contract,
                                                               note=rp.note, lead=rp.lead)
                break
            rp.contract_pending_repayment = None
            rp.type = ReconciledPaymentType.repayment
            rp.repayment = repayment

    @classmethod
    def give_days_grace_period(cls, contract, grace_period_in_days, approver=None, note=None):
        cls._check_if_contract_active(contract)
        if contract.offer.type == OfferType.time_based and contract.offer.payment_day_of_month:
            raise Error('DELAY_NOT_ALLOWED_FOR_DAY_OF_MONTH')
        if contract.offer.type == OfferType.usage_based:
            raise Error('CREDIT_UNIT_NOT_ALLOWED_FOR_DEVICE', contract.linked_device.get_allowed_units())
        hours_added = round(Decimal(grace_period_in_days)*24, 4)
        if abs(round(hours_added, 4)) > 10**8:
            raise Error('AMOUNT_TOO_HIGH')
        new_due_date = cls.get_next_payment_due_date_from_days_added(contract, grace_period_in_days)
        repayment = cls._create_repayment(
            contract=contract,
            date=datetime.now(),
            expected_date=contract.next_repayment_due_time,
            next_repayment_due_time=new_due_date,
            delay_given_in_hours=hours_added,
            credit_value=hours_added,
            discount_type=ContractRepaymentDiscountTypes.manual_delay,
        )
        cls._create_contract_event_object(
            contract=contract,
            time=repayment.time,
            type=ContractEventType.manual_delay,
            repayment=repayment,
            approver=approver,
            note=note if note else ''
        )
        cls._put_to_late_if_needed(contract)
        contract.update_cached_data(contract_terms_changed=True, volatile=True)
        return repayment

    @classmethod
    def create_adjustment_after_offer_change(cls, contract):
        cls._check_if_contract_active(contract, allow_completed=True)
        target_time = contract.next_repayment_due_time
        hours_added=Decimal(0)
        return cls._create_repayment(
            contract=contract,
            date=datetime.now(),
            expected_date=contract.next_repayment_due_time,
            next_repayment_due_time=target_time,
            delay_given_in_hours=hours_added,
            credit_value=hours_added,
            discount_type=ContractRepaymentDiscountTypes.offer_change_delay,
        )

    @classmethod
    def give_units_discount(cls, contract, discount_in_units, approver=None, note=None):
        discounted_amount = contract.get_value_of_credit(discount_in_units)
        return cls.give_amount_discount(contract, discounted_amount, approver, note)

    @classmethod
    def give_amount_discount(cls, contract, amount_discounted, approver=None, note=None):
        cls._check_if_contract_active(contract, amount_discounted)

        if contract.can_be_completed and contract.get_outstanding_balance() < amount_discounted:
            raise Error('DISCOUNT_MORE_THAN_LEFT_TO_PAY')

        new_due_date = cls.get_next_payment_due_date_from_amount_paid(contract, amount_discounted, allow_below_minimum=True)
        credit_value = contract.get_units_from_amount(amount_discounted, allow_below_minimum=True)
        repayment = cls._create_repayment(
            contract=contract,
            date=datetime.now(),
            expected_date=contract.next_repayment_due_time,
            next_repayment_due_time=new_due_date,
            credit_value=credit_value,
            amount=amount_discounted,
            amount_discounted=amount_discounted,
            discount_type=ContractRepaymentDiscountTypes.manual_discount
        )
        cls._create_contract_event_object(
            contract=contract,
            time=repayment.time,
            type=ContractEventType.manual_discount,
            repayment=repayment,
            approver=approver,
            note=note if note else ''
        )

        # We do that to clear pending payments that would be over the new amount due if any
        cls.clear_pending_payment_if_needed(contract)
        return repayment

    @classmethod
    def reverse_repayment(cls, repayment, approver=None, note=None, reconcile_to_client=False, force_allow_below_downpayment=False, cancelling=False):
        contract = repayment.contract
        if repayment.discount_type in [ContractRepaymentDiscountTypes.reversal, ContractRepaymentDiscountTypes.downpayment_reversal]:
            raise Error('REPAYMENT_REVERSAL_CANNOT_BE_REVERSED')

        if repayment.converse:
            raise Error('THE_REPAYMENT_HAS_ALREADY_BEEN_REVERSED')

        if not cancelling and repayment.addons.filter(lambda a: not a.cancelled):
            raise Error('This repayment is associated to some purchasing add-ons and cannot be reversed directly. Please cancel those add-ons.')

        if not cancelling and contract.lump_sum:
            raise Error('Repayments of Lump-sum contracts cannot be reversed')

        credit_value = -repayment.credit_value if repayment.credit_value is not None else None
        assert credit_value is not None, "This repayment is temporarily unavailable, please try again later or contact support if the issue persists"
        reversed_repayment = None
        if cancelling:
            next_repayment_due_date = contract.next_repayment_due_time
            reversed_repayment = cls._create_repayment_object(
            contract=contract,
            time=datetime.now(),
            expected_time=datetime.now(),
            next_repayment_due_time=next_repayment_due_date,
            credit_value=credit_value,
            amount=-repayment.amount,
            amount_paid=-repayment.amount_paid,
            amount_discounted=-repayment.amount_discounted,
            discount_type=ContractRepaymentDiscountTypes.downpayment_reversal if repayment.discount_type == ContractRepaymentDiscountTypes.downpayment else ContractRepaymentDiscountTypes.reversal,
            hours_late=-repayment.hours_late if repayment.hours_late is not None else None,
            amount_late=-repayment.amount_late if repayment.amount_late is not None else None
        )
        else:
            if contract.usage_based: 
                next_repayment_due_date = None

            else: 
                next_repayment_due_date = contract.offer_at(repayment.time).add_credit(contract.next_repayment_due_time, credit_value)
            
            reversed_repayment = cls._create_repayment(
                contract=contract,
                date=datetime.now(),
                expected_date=datetime.now(),
                next_repayment_due_time=next_repayment_due_date,
                credit_value=credit_value,
                amount=-repayment.amount,
                amount_paid=-repayment.amount_paid,
                amount_discounted=-repayment.amount_discounted,
                discount_type=ContractRepaymentDiscountTypes.downpayment_reversal if repayment.discount_type == ContractRepaymentDiscountTypes.downpayment else ContractRepaymentDiscountTypes.reversal,
                hours_late=-repayment.hours_late if repayment.hours_late is not None else None,
                allow_below_downpayment=force_allow_below_downpayment or (repayment.discount_type==ContractRepaymentDiscountTypes.downpayment)
            )


        repayment.converse = reversed_repayment
        reversed_repayment.processed = True
        cls._create_contract_event_object(
            contract=contract,
            time=reversed_repayment.time,
            type=ContractEventType.downpayment_reversal if repayment.discount_type == ContractRepaymentDiscountTypes.downpayment else ContractEventType.repayment_reversed,
            repayment=reversed_repayment,
            approver=approver,
            note=note if note else ''
        )
        
        for reconciled_payment in list(repayment.reconciled_payments):
            if not reconciled_payment.converse:
                ReconciledPaymentService.revert(reconciled_payment, cancelling=cancelling)
        if repayment.discount_type == ContractRepaymentDiscountTypes.downpayment:
            addons = contract.add_ons.select(lambda a: a.offer_version.offer.type != AddOnType.lump_sum).order_by(lambda a: a.offer_version.downpayment < 0)
            for addon in addons:
                for reconciled_payment in sorted(list(addon.reconciled_payments), key=lambda r: r.amount < 0):
                    if not reconciled_payment.converse:
                        ReconciledPaymentService.revert(reconciled_payment, cancelling=cancelling)
        return reversed_repayment

    @classmethod
    def get_discounted_amount_from_amount_paid(cls, contract, amount_paid, time=None):
        time_for_amount_paid = contract.get_units_from_amount(amount_paid, allow_below_minimum=True, time=time)
        value_of_time_given = contract.get_value_of_credit(time_for_amount_paid, time=time)
        return round(value_of_time_given - amount_paid, 2)

    @classmethod
    def get_next_payment_due_date_from_amount_paid(cls, contract, amount_paid, allow_below_minimum=True, time=None):
        if contract.usage_based:
            return None
        time_bought = contract.get_units_from_amount(amount_paid, allow_below_minimum, time)
        if contract.offer.is_monthly:
            next_payment_date = cls.get_next_payment_due_date_from_days_added(contract=contract, months_added=time_bought)
            if contract.offer.payment_day_of_month:
                next_payment_date = set_day_of_month(next_payment_date, contract.offer.payment_day_of_month)
            return next_payment_date
        return cls.get_next_payment_due_date_from_days_added(contract=contract, days_added=time_bought)

    @staticmethod
    def get_next_payment_due_date_from_days_added(contract, days_added=None, months_added=None):
        base_date = contract.next_repayment_due_time
        if contract.offer.forgive_lateness:
            base_date = max(datetime.now(), base_date)
        if months_added is not None:
            return add_months(base_date, months_added)
        extra_time = timedelta(days=float(days_added))
        if (datetime.min-base_date) > extra_time:
            return datetime.min
        if (datetime.max-base_date) < extra_time:
            return datetime.max
        return base_date + extra_time

    @classmethod
    def check_can_create_repayment(cls, contract, amount_paid, time=None):
        cls._check_if_contract_active(contract)
        if contract.status == ContractStatus.paused:
            if not SettingsService.get_setting('AllowPaymentsFromPausedContractsAsPending'):
                raise Error('Cannot reconciliate to paused contracts cause setting is disabled')
            return False
        if not SettingsService.get_setting('EnableContractPaymentsForReversedDownpayments') and not contract.downpayment_fully_paid: 
            if amount_paid < contract.offer.registration_fee:
                return False
            else: return True
        is_first_repayment_with_day_of_month = cls._check_if_first_repayment_with_day_of_month(contract)
        if not cls._amount_paid_is_above_minimum(contract, amount_paid, time) and not is_first_repayment_with_day_of_month:
            return False
        return True

    @classmethod
    def _create_repayment_from_amount_paid(cls, contract, amount_paid, time=None):
        if not SettingsService.get_setting('EnableContractPaymentsForReversedDownpayments') and not contract.downpayment_fully_paid and amount_paid >= contract.offer.registration_fee:
            amount_discounted = 0
            next_payment_due_date = contract.next_repayment_due_time
            credit_value = 0
            total_amount = amount_paid
            discount_type = ContractRepaymentDiscountTypes.downpayment
        else: 
            amount_discounted = cls.get_discounted_amount_from_amount_paid(contract, amount_paid, time)
            next_payment_due_date = cls.get_next_payment_due_date_from_amount_paid(contract, amount_paid, time=time, allow_below_minimum=True)
            credit_value = contract.get_units_from_amount(amount_paid, time=time, allow_below_minimum=True)
            total_amount = amount_paid + amount_discounted
            discount_type = ContractRepaymentDiscountTypes.prepayment if amount_discounted > 0 else ''

        return cls._create_repayment(
            contract=contract,
            date=time or datetime.now(),
            next_repayment_due_time=next_payment_due_date,
            credit_value=credit_value,
            amount=total_amount,
            amount_paid=amount_paid,
            amount_discounted=amount_discounted,
            discount_type=discount_type
        )

    @classmethod
    def _amount_paid_is_above_minimum(cls, contract, amount_paid, time=None):
        if amount_paid <= 0 and contract.status != ContractStatus.overpaid:
            return False
        minimum_amount = contract.minimum_price_at(time)
        return minimum_amount <= amount_paid or cls.amount_is_sufficient_for_completion(
            contract, amount_paid
        ) or (minimum_amount >= amount_paid and contract.status == ContractStatus.overpaid)

    @classmethod
    def get_device_mode_from_offer(cls, offer):
        # We check if the device should be PAYG or not
        if offer.type == OfferType.lump_sum:
            return DeviceMode.disabled
        elif offer.type in [OfferType.time_based, OfferType.loan]:
            return DeviceMode.time
        elif offer.type == OfferType.usage_based:
            return DeviceMode.credit
        else:
            raise Error('UNSUPPORTED_DEVICE_MODE')

    @classmethod
    def sync_device_status_from_contract(cls, device, contract):
        if device:
            device.Mode = cls.get_device_mode_from_offer(contract.offer)
            device.ActiveUntil = contract.next_repayment_due_time

    @classmethod
    def create_first_repayment_on_contract(cls, contract, acting_user):
        offer = contract.offer
        deposit_value = offer.registration_fee
        credit_value = offer.free_credit_at_start
        if offer.type != OfferType.usage_based:
            if offer.is_monthly:
                next_repayment_due_time = add_months(
                    contract.start_time, offer.free_credit_at_start
                )
            else:
                next_repayment_due_time = contract.start_time + timedelta(
                    days=int(offer.free_credit_at_start)
                )
        else:
            next_repayment_due_time = None

        lead = contract.lead
        discounted = max(0, deposit_value-lead.already_paid)
        this_repayment = cls._create_repayment(
            contract=contract,
            date=contract.start_time,
            expected_date=contract.start_time,
            next_repayment_due_time=next_repayment_due_time,
            credit_value=credit_value,
            amount=deposit_value,
            amount_paid=min(deposit_value, lead.already_paid),
            amount_discounted=discounted,
            discount_type=ContractRepaymentDiscountTypes.downpayment,
            addons=lead.purchasing_addons
        )
        orm.flush()
        contract.contract_events.select(
            lambda e: e.type == ContractEventType.creation
        ).get().repayment = this_repayment

        # We link it to the reconciled payment
        for reconciled in contract.lead.reconciled_payments:
            if reconciled.type == ReconciledPaymentType.initial_payment:
                reconciled.repayment = this_repayment
            elif reconciled.type == ReconciledPaymentType.repayment_pending:
                reconciled.contract_pending_repayment = contract
            elif reconciled.type == ReconciledPaymentType.blocked_during_lead_editing:
                raise Exception('Registering lead with amount blocked during edition')

        if -lead.purchasing_addons_amount > lead.downpayment:
            ContractRepaymentService.give_off_taking_discount(
                contract,
                -lead.purchasing_addons_amount-discounted,
                addons=lead.purchasing_addons,
                approver=acting_user
            )

        return this_repayment

    @classmethod
    def amount_is_sufficient_for_completion(cls, contract, amount):
        max_rounding_discount = SettingsService.get_setting('MaxRoundingDiscount')
        return contract.can_be_completed and abs(
            contract.get_outstanding_balance() - amount
        ) < max_rounding_discount
    
    @classmethod
    def create_off_taking_client_payment(cls, contract, amount, account, time):
        if not contract.status == ContractStatus.overpaid:
            raise Error('Cannot pay client if contract is not overpaid')
        repayment = cls._create_repayment_object(
            contract=contract,
            time=time,
            expected_time=time,
            next_repayment_due_time=time,
            amount=amount,
            amount_discounted=amount,
            credit_value=0,
            hours_late=0,
            amount_late=0,
            discount_type=ContractRepaymentDiscountTypes.payment_to_client
        )
        reconciled = ReconciledPaymentService.create_reconciliation(
            account=account, 
            time=time,
            amount=amount, 
            repayment_amount=amount,
            type=ReconciledPaymentType.payment_to_client
        )
        reconciled.repayment = repayment
        if contract.can_be_completed and contract.get_outstanding_balance() == 0:
            cls.finish_contract(contract, time, skip_check=True)
        return reconciled

    @classmethod
    def give_off_taking_discount(cls, contract, amount, addons, approver):
        note = "Purchasing Addons"
        discounted_amount = amount

        if contract.status == ContractStatus.paused:
            raise Error('You cannot add a purchasing addon to a paused contract')

        expected_time = contract.next_repayment_due_time if contract.offer.type != OfferType.usage_based else None
        new_due_date = cls.get_next_payment_due_date_from_amount_paid(
            contract, discounted_amount, allow_below_minimum=True
        )
        date=datetime.now()
        credit_value = contract.get_units_from_amount(discounted_amount, allow_below_minimum=True)
        repayment = cls._create_repayment(
            contract=contract,
            date=date,
            expected_date=expected_time,
            next_repayment_due_time=new_due_date,
            credit_value=credit_value,
            amount=discounted_amount,
            amount_discounted=discounted_amount,
            discount_type=ContractRepaymentDiscountTypes.purchasing_addon,
            addons=addons,
            offtaking=True
        )
        if contract.can_be_completed and contract.get_outstanding_balance() < 0:
            from payg_loan_system.contracts.services.contract_termination_service import ContractTerminationService
            ContractTerminationService.overpay_contract(contract, approver, discounted_amount, repayment, note)
        return repayment

    @classmethod
    def _create_repayment(cls, contract, date, next_repayment_due_time=None, credit_value=None, expected_date=None,
                          delay_given_in_hours=None, amount_paid=None, amount_discounted=None,
                          amount=None, discount_type='', hours_late=None, allow_below_downpayment=False, addons=None, offtaking=False):

        #Pre process input data
        last_repayment = contract._get_last_repayment(date)
        expected_date = expected_date or contract.next_repayment_due_time \
            if contract.offer.type != OfferType.usage_based else None
        if last_repayment and expected_date and last_repayment.time > expected_date:
            expected_date = last_repayment.time
        amount_paid = amount_paid or Decimal(0)
        amount_discounted = amount_discounted or Decimal(0)
        calculated_amount = amount_paid + amount_discounted
        if amount and amount != calculated_amount:
            raise Error('AMOUNT_DOESNT_MATCH_PAID_AND_DISCOUNT')
        amount = calculated_amount

        if credit_value:
            credit_value = round(credit_value, 2)
        #Reactivate completed contracts
        if contract.status == ContractStatus.completed:
            cls.reactivate_contract(contract, date, sync_device=False)
            # we cannot sync activation here since the value will be modified just below

        if cls.amount_is_sufficient_for_completion(contract, amount):
            if contract.get_outstanding_balance() > amount:
                difference = contract.get_outstanding_balance() - amount
                cls._create_repayment_object(
                    contract=contract,
                    time=date,
                    expected_time=expected_date,
                    next_repayment_due_time=expected_date,
                    amount=difference,
                    amount_discounted=difference,
                    hours_late=0,
                    amount_late=0,
                    discount_type=ContractRepaymentDiscountTypes.rounding,
                    addons=addons or []
                )
            cls.finish_contract(contract, date, skip_check=True)

        if not offtaking:
            cls._check_if_repayment_amount_allowed(contract, amount, allow_below_downpayment)

        def sign(x):
            return 1 if x > 0 else -1
        if contract.offer.type != OfferType.usage_based and not (offtaking and contract.status in [ContractStatus.overpaid, ContractStatus.completed]):
            hours_late = hours_late or ceil(timedelta_to_hours(date - expected_date)*Decimal('10000'))/Decimal('10000')
            amount_late = contract.get_value_of_credit(hours_late/Decimal('24'))
            if abs(hours_late) > 10**10:
                LogAPI.Warning('Hours late more than allowed in Database')
                hours_late = round(sign(hours_late)*9.9**10, 2)
            if abs(amount_late) > 10**10:
                LogAPI.Warning('amount_late more than allowed in Database')
                amount_late = round(sign(amount_late)*9.9**10, 2)
        else:
            hours_late, amount_late = None, None
            if offtaking and contract.status in [ContractStatus.overpaid, ContractStatus.completed]:
                hours_late, amount_late = 0,0
        if contract.offer.type == OfferType.usage_based:
            this_repayment = cls._create_repayment_object(
                contract=contract,
                time=date,
                expected_time=expected_date,
                next_repayment_due_time=next_repayment_due_time,
                credit_unit=contract.linked_device.credit_unit,
                credit_value=credit_value,
                amount=amount,
                amount_paid=amount_paid,
                amount_discounted=amount_discounted,
                delay_given_in_hours=delay_given_in_hours if delay_given_in_hours else 0,
                discount_type=discount_type,
                hours_late=hours_late,
                amount_late=amount_late,
                addons=addons or []
            )
        else:
            if abs(credit_value) > MAX_CREDIT_PER_REPAYMENT_ALLOWED:
                raise Error(f'Impossible to create a repayment for more than {MAX_CREDIT_PER_REPAYMENT_ALLOWED/24/365} years', code="MAX_CREDIT_PER_REPAYMENT_EXCEEDED")
            this_repayment = cls._create_repayment_object(
                contract=contract,
                time=date,
                expected_time=expected_date,
                next_repayment_due_time=next_repayment_due_time,
                credit_value=credit_value,
                amount=amount,
                amount_paid=amount_paid,
                amount_discounted=amount_discounted,
                delay_given_in_hours=delay_given_in_hours if delay_given_in_hours else 0,
                discount_type=discount_type,
                hours_late=hours_late,
                amount_late=amount_late,
                addons=addons or []
            )
        contract.next_repayment_due_time = next_repayment_due_time
        contract.update_device_status(credit_value=credit_value)
        add_hook_after_commit(db, 'contract_payment', this_repayment.get_serialized_object())

        cls._put_to_late_if_needed(contract)

        return this_repayment
    
    @classmethod
    def _put_to_late_if_needed(cls, contract):
        enable_late_status = SettingsService.get_setting('EnableLateStatus')
        days_late_for_late_status = SettingsService.get_setting('DaysLateForLateStatus')
        if contract.status == ContractStatus.late:
            if not enable_late_status or contract.next_repayment_due_time >= (datetime.now() - timedelta(days=days_late_for_late_status)):
                contract.status = ContractStatus.active
        elif enable_late_status and contract.status == ContractStatus.active and contract.next_repayment_due_time and contract.next_repayment_due_time <= (datetime.now() - timedelta(days=days_late_for_late_status)):
            contract.status = ContractStatus.late
    
    @classmethod
    def finish_contract(cls, contract, date=None, skip_check=False):
        if not date:
            date = select(rp.time for rp in contract.repayments).max()
        if not skip_check:
            difference = contract.get_outstanding_balance()
            if difference:
                if difference < SettingsService.get_setting('MaxRoundingDiscount'):
                    ContractRepaymentService._create_repayment_object(
                        contract=contract,
                        time=date,
                        expected_time=contract.next_repayment_due_time,
                        next_repayment_due_time=contract.next_repayment_due_time,
                        amount=difference,
                        amount_discounted=difference,
                        hours_late=0,
                        amount_late=0,
                        discount_type=ContractRepaymentDiscountTypes.rounding,
                    )
                else:
                    raise Error('The contract cannot be completed with amount left to pay')
        contract.status = ContractStatus.completed
        contract.end_time = date
        cls._create_contract_event_object(
            contract=contract,
            time=date,
            type=ContractEventType.completion
        )
        cls._send_data_to_hook_completed(contract)

    @classmethod
    def reactivate_contract(cls, contract, date=None, sync_device=True):
        if contract.client.first_active_or_late_contract and not SettingsService.get_setting('AllowMultipleContracts'):
            raise Error(f'Contract {contract.reference} cannot be reactivated since the client already has an active contract')
        contract.status = ContractStatus.active
        contract.end_time = None
        contract.repossession_time = None

        cls._create_contract_event_object(
            contract=contract,
            time=date or datetime.now(),
            type=ContractEventType.undo_completion
        )
        if contract.next_repayment_due_time < datetime.now():
            contract.next_repayment_due_time = datetime.now()
        cls.sync_device_status_from_contract(contract.linked_device, contract)
        if DeviceAPIService.device_can_auto_activate(contract.linked_device) and sync_device:
            return [sync_activation(contract=contract, allow_negative=True)]
        return []

    @classmethod
    def _create_repayment_object(cls, **kwargs):
        return ContractRepayment(**kwargs)

    @classmethod
    def _create_contract_event_object(cls, **kwargs):
        return ContractEvent(**kwargs)

    @classmethod
    def _check_if_repayment_amount_allowed(cls, contract, amount, allow_below_downpayment):
        if amount >= 0:
            return
        new_balance = contract.get_cumulative_amount_repaid_without_deposit()
        if allow_below_downpayment:
            new_balance += contract.offer.registration_fee
        if new_balance + amount < 0:
            raise Error('NEGATIVE_CONTRACT_BALANCE_FORBIDDEN')

    @classmethod
    def _check_if_contract_active(cls, contract, amount_discounted=None, allow_completed=False):
        if contract.status == ContractStatus.completed and (not allow_completed) and (not amount_discounted or amount_discounted > 0):
            raise Error('CONTRACT_COMPLETED')
        if contract.status == ContractStatus.defaulted and not hasattr(contract, 'allow_defaulted'): # needed for a bugfix, can be removed later
            raise Error('CONTRACT_DEFAULTED')
        if contract.status == ContractStatus.paused:
            raise Error('CONTRACT_PAUSED')
    
    @classmethod
    def process_contract_with_unprocessed_repayments(cls, contract):
        answer = None
        last_repayment_processed = select(r.time for r in contract.repayments if r.processed)
        if last_repayment_processed.count() > 0:
            last_repayment_processed_time = last_repayment_processed.max()
            repayments_to_fix = contract.repayments.filter(lambda r: r.time > last_repayment_processed_time and not r.processed)
            print(f'CONTRACT {contract.reference}, IDs: {[r.id for r in repayments_to_fix]}')
            print(repayments_to_fix.count())
            answer = [sync_activation(contract, repayments=repayments_to_fix)]
            for repayment in contract.repayments.filter(lambda r: not r.processed):
                repayment.processed = True
            orm.commit()
        if answer:
            MessageService.send_answer_to_person(answer, contract.client.person)

    @classmethod
    def _send_data_to_hook_completed(cls, contract):
        client = contract.client
        # In unit tests we often pass stubbed contracts; Pony cannot build queries with them.
        try:
            last_repayment = (
                ContractRepayment.select(lambda r: r.contract == contract)
                .order_by(orm.desc(ContractRepayment.time))
                .first()
            )
        except TypeError:
            last_repayment = None

        try:
            completion_event = (
                ContractEvent.select(lambda ce: ce.contract == contract and ce.type == ContractEventType.completion)
                .order_by(orm.desc(ContractEvent.time))
                .first()
            )
        except TypeError:
            completion_event = None
        formatted_data = {
            'contract_reference': contract.reference,
            'client_id': client.id,
            'client_name': client.person.name,
            'client_surname': client.person.surname,
            'total_loan_value': contract.get_total_value(),
            'repayment_id': last_repayment.id if last_repayment else None,
            'contract_event_id': completion_event.id if completion_event else None,
            'device_serial_number': contract.linked_device.get_display_name() if contract.linked_device else None
        }
        add_hook_after_commit(db, 'contract_completed', formatted_data)
