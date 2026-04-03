from datetime import datetime
from core_system.users.models.user_model import User
from payg_loan_system.actions.helpers.code_error import ConfigurationError, handle_device_code_error
from payg_loan_system.contracts.models.reconciled_payment_type import ReconciledPaymentType
from payg_loan_system.contracts.models.repayment_discount_types import ContractRepaymentDiscountTypes
from payg_loan_system.devices.device_api.device_api_errors import DeviceAPIError
from payg_loan_system.devices.model.device_mode import DeviceMode
from payg_loan_system.payments.models.wallet import PaymentWalletOwner
from shared.api_helpers.hook_helpers.process_hook import process_hook
from pony import orm
from shared.logger.loggers import Error, LogAPI
from shared.helpers.numbers import round_if_exists
from shared.services.settings_service import SettingsService
from payg_loan_system.offers.models import OfferType
from payg_loan_system.contracts.services.reconciled_payment_service import ReconciledPaymentService
from payg_loan_system.contracts.services.contract_repayment_service import ContractRepaymentService
from payg_loan_system.actions.activation import positive
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from payg_loan_system.contracts.services.contract_repayment_service import ContractStatus
from sales_system.leads.services.lead_status_change_service import LeadStatusChangeService
from pony.orm import db_session
import config


class ReconciliationService:

    @classmethod
    def get_answer_for_lead(cls, lead, payment=None, amount=None, account=None, check_awaiting_payment=True, autoreconcile_from_client=True, user=None, origin_reconciled_payment=None):
        note = f'Manually reconciled by {user.full_name} ({user.id})' if user else ''
        something_reconciled = False
        with db_session:
            if check_awaiting_payment:
                cls._can_be_paid(lead)
            account = payment.PaymentWallet if payment else account
            if not SettingsService.get_setting('AllowPayingLeadWithOwnedAccount'):
                cls._check_if_payment_account_is_not_used(lead, account)
            if SettingsService.get_setting('AutoLinkAccountWhenPayingDownpayment') and not account.owned:
                account.lead = lead
                PaymentWalletOwner(
                    wallet=account,
                    lead=lead,
                    date=datetime.now(),
                    balance=account.get_balance()
                )
            if payment and not payment.orphaned:
                raise Error('PAYMENT_ALREADY_USED')
            if not lead.offer_editing_locked:
                reconciliation = ReconciledPaymentService.create_reconciliation(
                    lead=lead,
                    type=ReconciledPaymentType.blocked_during_lead_editing,
                    payment=payment,
                    account=account,
                    amount=amount,
                    note=note,
                    origin_reconciled_payment=origin_reconciled_payment
                )
                amount = amount-reconciliation.amount if amount else amount
                something_reconciled = True
            already_paid = True
            if not lead.deposit_paid_not_blocked: # TO DO: change back to deposit_paid when bug fixed
                already_paid = False
                if lead.offer_editing_locked:
                    for addon in lead.loan_addons.filter(lambda a: a.downpayment < 0 and a.already_paid > a.downpayment):
                        recon = ReconciledPaymentService.create_reconciliation(
                            lead=lead,
                            addon=addon,
                            type=ReconciledPaymentType.addon,
                            payment=payment,
                            account=account,
                            amount=amount,
                            note=note,
                            origin_reconciled_payment=origin_reconciled_payment
                        )
                        something_reconciled = True
                        amount = amount-recon.amount if amount else amount
                for addon in lead.lump_sum_addons.filter(lambda a: not a.paid_for_leads and not a.free).order_by(lambda l: l.time_created):
                    if not ((payment and payment.orphaned) or (amount and amount > 0)) or (payment and payment.remaining == 0): # if no money left
                        break
                    recon = ReconciledPaymentService.create_reconciliation(
                        lead=lead,
                        addon=addon,
                        type=ReconciledPaymentType.purchasing_addon if addon.offer_version.offer.purchasing_addon else ReconciledPaymentType.addon,
                        payment=payment,
                        account=account,
                        amount=amount,
                        note=note,
                        origin_reconciled_payment=origin_reconciled_payment
                    )
                    something_reconciled = True
                    amount = amount-recon.amount if amount else amount
                for addon in lead.loan_addons.filter(lambda a: a.already_paid < a.downpayment).order_by(lambda l: l.time_created):
                    if not ((payment and payment.orphaned) or (amount and amount > 0)) or (payment and payment.remaining == 0): # if no money left
                        break
                    recon = ReconciledPaymentService.create_reconciliation(
                        lead=lead,
                        addon=addon,
                        type=ReconciledPaymentType.addon,
                        payment=payment,
                        account=account,
                        amount=amount,
                        note=note,
                        origin_reconciled_payment=origin_reconciled_payment
                    )
                    something_reconciled = True
                    amount = amount-recon.amount if amount else amount
                if ((payment and payment.orphaned) or (amount and amount > 0)) and (not lead.deposit_paid_not_blocked): # if still has money and downpayment not completely paid, we put it actual downpayment
                    reconciliation = ReconciledPaymentService.create_reconciliation(
                        lead=lead,
                        type=ReconciledPaymentType.initial_payment,
                        payment=payment,
                        account=account,
                        amount=amount,
                        note=note,
                        origin_reconciled_payment=origin_reconciled_payment
                    )
                    amount = amount-reconciliation.amount if amount else amount
                    something_reconciled = True
            money_left = payment.orphaned if payment else (amount and amount > 0)
            if lead.future_contract_value+lead.lump_sum_addons_value < lead.downpayment:
                raise Exception('The downpayment cannot be more than the total value. ')
            assert not lead.offer.can_be_completed or lead.maximum_pending >= 0, f"Lead maximum pending calculation error. Lead ID: [{lead.id}]. Max Pending: [{lead.maximum_pending}]"
            if money_left and (not lead.offer.can_be_completed or lead.maximum_pending): # if still has money we put it as pending
                reconciliation = ReconciledPaymentService.create_reconciliation(
                    lead=lead,
                    type=ReconciledPaymentType.repayment_pending,
                    payment=payment,
                    account=account,
                    amount=amount,
                    note=note,
                    origin_reconciled_payment=origin_reconciled_payment
                )
                amount = amount-reconciliation.amount if amount else amount
                something_reconciled = True
            if payment:
                payment.processed = True
        if not something_reconciled:
            return []
        with db_session:
            LeadStatusChangeService.update(lead, autoreconcile_from_client=autoreconcile_from_client) #update to paid
            if not already_paid and lead.deposit_paid:
                process_hook('lead_edited', lead.get_serialized_object())
            if lead.deposit_paid:
                answer = [{
                    'success': True,
                    'status': 'LEAD_PAY_DEPOSIT_SUCCESS',
                    'deposit_value': round_if_exists(lead.downpayment),
                    'balance': round_if_exists(account.get_balance()),
                    'transaction_id': payment.Reference if payment else ''
                }]
                if SettingsService.get_setting('AutoRegisterLeadWithDownpaymentAndDevice') and lead.approved and not lead.based_on_lead:
                    device = lead.allocated_device
                    if device and not lead.forms_missing_for_registration and not SettingsService.get_setting('ContractDeviceRestrictions') == 'no_device':
                        acting_user = User.get(username=config.SYSTEM_EMAIL)
                        from payg_loan_system.actions.registration import register_lead
                        answer += register_lead(acting_user=acting_user, this_lead=lead, this_device=device)
                    elif not device and lead.offer and not lead.offer.linked_to_product and not SettingsService.get_setting('ContractDeviceRestrictions') == 'no_device':
                        acting_user = User.get(username=config.SYSTEM_EMAIL)
                        from payg_loan_system.actions.registration import register_lead
                        answer += register_lead(acting_user=acting_user, this_lead=lead, this_device=None)
                return answer
            return [{
                'success': True,
                'status': 'LEAD_INSUFFICIENT_BALANCE',
                'deposit_value': round_if_exists(lead.downpayment),
                'already_paid': round_if_exists(lead.already_paid),
                'still_to_pay': round_if_exists(lead.left_to_pay),
                'contract_reference': lead.future_contract_reference,
                'transaction_id': payment.Reference if payment else ''
                
            }]

    @staticmethod
    def _can_be_paid(lead):
        if lead.offer_editing_locked and not (lead.awaiting_payment or lead.awaiting_delivery):
            raise Error('LEAD_NOT_AWAITING_PAYMENT')
        if not lead.offer:
            raise Error('LEAD_HAS_NO_OFFER')

    @staticmethod
    def _check_if_payment_account_is_not_used(lead, account):
        if account.client:
            raise Error('PAYMENT_ACCOUNT_ALREADY_OWNED_BY_CLIENT', {'client_id': account.client.id})
        if account.lead and account.lead != lead:
            raise Error('PAYMENT_ACCOUNT_ALREADY_OWNED_BY_LEAD', {'lead_id': account.lead.id})

    @classmethod
    def get_answer_for_addons(cls, contract, addons, payment=None, amount=None, account=None, user=None, force_time=None, paying_downpayment=False, origin_reconciled_payment=None):
        answer = []
        note = f'Manually reconciled by {user.full_name} ({user.id})' if user else ''
        with db_session:
            remaining = payment.remaining if payment else amount
            for addon in addons:
                if addon.cancelled or addon.paid or addon.downpayment_paid or (
                    addon.offer_version.offer.purchasing_addon and (
                        not addon.contract or
                        addon.contract.offer.type != OfferType.lump_sum
                    )
                ):
                    continue
                reconciled = ReconciledPaymentService.create_reconciliation(
                    payment=payment, account=account, amount=remaining, addon=addon, note=note, origin_reconciled_payment=origin_reconciled_payment
                )
                remaining -= reconciled.amount
                wallet = account or payment.PaymentWallet
                if not paying_downpayment:
                    answer.append(cls._get_paid_addon_answer(addon, wallet, payment) \
                        if addon.paid or addon.downpayment_paid else cls._get_unpaid_addon_answer(addon, payment))
                if not remaining:
                    if paying_downpayment and not (addon.downpayment_paid and contract.offer.registration_fee == 0):
                        paying_downpayment = False
                        answer += [cls._get_incomplete_downpayment_answer_for_contract(contract, payment)]
                    break
        if (remaining and contract.status != ContractStatus.completed) or (paying_downpayment and contract.offer.registration_fee == 0):
            answer += cls.create_repayment_and_get_answer(contract, payment, remaining, account, user, force_time=force_time, origin_reconciled_payment=origin_reconciled_payment)
        elif payment:
            with db_session:
                payment.processed = True
        return answer

    @staticmethod
    def _get_incomplete_downpayment_answer_for_contract(contract, payment):
        return {
                'success': True,
                'status': 'LEAD_INSUFFICIENT_BALANCE',
                'deposit_value': round_if_exists(contract.get_total_downpayment()),
                'already_paid': round_if_exists(contract.loan_addons_downpayments_paid+contract.pending_amount),
                'still_to_pay': round_if_exists(contract.get_total_downpayment()-contract.loan_addons_downpayments_paid-+contract.pending_amount),
                'contract_reference': contract.reference,
                'transaction_id': payment.Reference if payment else ''
                
            }

    @staticmethod
    def _get_paid_addon_answer(addon, wallet, payment):
        return {
            'success': True,
            'status': 'ADDON_PAYMENT_SUCCESS',
            'total_amount': round_if_exists(addon.downpayment or addon.total_amount),
            'reference': addon.reference,
            'balance': round_if_exists(wallet.get_balance()),
            'transaction_id': payment.Reference if payment else ''
        }

    @staticmethod
    def _get_unpaid_addon_answer(addon, payment):
        return {
            'success': True,
            'status': 'ADDON_PAYMENT_INSUFFICIENT_BALANCE',
            'total_amount': round_if_exists(addon.downpayment or addon.total_amount),
            'reference': addon.reference,
            'already_paid': round_if_exists(addon.already_paid),
            'remaining_to_pay': round_if_exists(addon.to_pay),
            'transaction_id': payment.Reference if payment else ''
        }

    @staticmethod
    @db_session
    def get_answer_for_user(user, payment=None, amount=None, account=None):
        reconciled = ReconciledPaymentService.create_reconciliation(payment=payment, account=account,
                                                                    amount=amount, user=user)
        if payment:
            payment.processed = True
        return [{
            'success': True,
            'status': 'USER_PAYMENT_SUCCESS',
            'total_amount': round_if_exists(reconciled.amount)
        }]

    @staticmethod
    def get_answer_for_adjustment(payment=None, amount=None, account=None, note=None):
        reconciled = ReconciledPaymentService.create_reconciliation(
            payment=payment,
            account=account,
            amount=amount, 
            type=ReconciledPaymentType.manual_adjustment,
            note=note or ''  
        )
        return [{
            'success': True,
            'status': 'BALANCE_ADJUSTMENT_SUCCESS',
            'total_amount': round_if_exists(reconciled.amount)
        }]

    @staticmethod
    def get_answer_for_overpaid_contract(contract, payment=None, amount=None, account=None, note=None, origin_reconciled_payment=None):
        overpaid_amount = payment.remaining if payment else amount
        if SettingsService.get_setting('AllowPendingPayments'):
            reconciled = ReconciledPaymentService.create_reconciliation(
                payment=payment,
                account=account,
                amount=amount,
                type=ReconciledPaymentType.payment_pending_reconciliation,
                note=note or '',
                person=contract.client.person,
                origin_reconciled_payment=origin_reconciled_payment
            )
            overpaid_amount = reconciled.amount
        if payment:
            payment.processed = True
        return [{
            'success': True,
            'status': 'LOAN_OVERPAYMENT',
            'amount_paid': round_if_exists(overpaid_amount),
            'total_overpaid': round_if_exists(contract.client.get_total_overpaid()),
            'total_to_pay': round_if_exists(contract.get_total_value()),
            'transaction_id': payment.Reference if payment else ''
        }]

    @classmethod
    def get_answer_for_contract(cls, contract, payment=None, amount=None, account=None, user=None, force_time=None, origin_reconciled_payment=None):
        addons_with_priority = False
        with db_session:
            addons = []
            paying_downpayment = False
            if not SettingsService.get_setting('EnableContractPaymentsForReversedDownpayments'):
                paying_downpayment = True
                addons += contract.loan_addons.filter(
                    lambda a: a.already_paid != a.downpayment and a.lead and not a.time_canceled
                ).order_by(
                    lambda a: a.offer_version.downpayment > 0
                )[:]
            elif SettingsService.get_setting('AutomaticAddOnReconciliation'):
                addons += contract.unpaid_addons[:]
            if addons:
                addons_with_priority = True
        if addons_with_priority and (
            payment or (account and amount)
        ) and contract.status != ContractStatus.cancelled:
            # add-ons reconciliation don't support using pending payments
            return cls.get_answer_for_addons(
                contract, addons, payment, amount, account, user,
                force_time=force_time, paying_downpayment=paying_downpayment, origin_reconciled_payment=origin_reconciled_payment
            )
        if contract.status in [ContractStatus.completed, ContractStatus.cancelled]:
            if contract.client.first_active_or_late_contract:
                return cls.get_answer_for_contract(
                    contract.client.first_active_or_late_contract,
                    payment, amount, account, user, force_time, origin_reconciled_payment=origin_reconciled_payment
                )
            with db_session:
                eligible_leads = contract.client.person.lead.filter(lambda l: l.can_receive_payment)
                if eligible_leads.count() == 1:
                    return cls.get_answer_for_lead(eligible_leads.first(), payment, amount, account, origin_reconciled_payment=origin_reconciled_payment)
                return cls.get_answer_for_overpaid_contract(contract, payment, amount, account, origin_reconciled_payment=origin_reconciled_payment)
        return ReconciliationService.create_repayment_and_get_answer(
            contract, payment, amount, account, user, force_time=force_time, origin_reconciled_payment=origin_reconciled_payment
        )

    @classmethod
    def create_repayment_and_get_answer(cls, contract, payment=None, amount=None, account=None, user=None, force_time=None, origin_reconciled_payment=None):
        note = f'Manually reconciled by {user.full_name} ({user.id})' if user else ''
        force_time = force_time or (datetime.now() if user else None)
        with db_session:
            repayments = ContractRepaymentService.repay_and_reconcile(
                contract, payment, account, amount, note, force_time=force_time, origin_reconciled_payment=origin_reconciled_payment
            )
            if payment:
                payment.processed = True
        # This can crash and cause session issue so we do it separately
        # Everything below is actually a different "transaction"
        # as we already saved (1st transaction) and routed the payment (2nd transaction)
        with orm.db_session:
            answer = []
            if repayments and repayments[0].discount_type == ContractRepaymentDiscountTypes.downpayment:
                answer += [{
                    'success': True,
                    'status': 'LEAD_PAY_DEPOSIT_SUCCESS',
                    'deposit_value': round_if_exists(contract.get_total_downpayment()),
                    'balance': round_if_exists(account.get_balance() if account else 0),
                    'transaction_id': payment.Reference if payment else ''
                }]
                repayments = repayments[1:]
            if repayments:
                answer += cls._generate_activation_answer_if_possible(contract, repayments)
                if amount: # we need this in case we continue reconciling things for completed contracts
                    amount = amount - sum([r.amount_paid for r in repayments])
            if contract.pending_amount and contract.status == ContractStatus.paused:
                answer += cls._get_pending_payment_answer_for_paused_contract(contract, payment)
            elif contract.pending_amount and contract.status != ContractStatus.paused:
                answer += cls._get_balance_insufficient_answer(
                    contract, success=bool(repayments), payment=payment
                ) if contract.downpayment_fully_paid else [
                    cls._get_incomplete_downpayment_answer_for_contract(contract, payment)
                ]
            if contract.status == ContractStatus.completed and payment and payment.orphaned:
                orm.flush()
                answer += cls.get_answer_for_contract(
                    contract, payment, amount, account, user, force_time
                )
            return answer

    @classmethod
    def _generate_activation_answer_if_possible(cls, contract, repayments):
        repayments_data = cls._get_repayments_data(contract, repayments)
        device = contract.linked_device

        # Some offers/contracts are valid without a linked device.
        # In that case we still reconcile payment but skip activation logic.
        if not device:
            if contract.status == ContractStatus.completed:
                return [dict(repayments_data, status='LOAN_REPAYMENT_COMPLETED_NO_TOKEN')]
            return [cls.get_as_no_token(repayments_data)]

        if device.Mode not in [DeviceMode.credit, DeviceMode.disabled] and contract.offer.type == OfferType.usage_based:
            LogAPI.Warning("Device with usage based offer but not in credit mode", {'device_sn': device.composed_serial})

        can_auto_activate = DeviceAPIService.device_can_auto_activate(device)

        if contract.status == ContractStatus.completed:
            unlock_allowed = contract.offer.automatic_unlock_code_sending or contract.offer.type == OfferType.lump_sum
            if unlock_allowed and can_auto_activate:
                device.Mode = DeviceMode.disabled
                try:
                    answer_code = DeviceAPIService.sync_device_settings(device, repayments=repayments)
                    if DeviceAPIService.device_requires_answer_code(device):
                        return [dict(repayments_data, status='LOAN_REPAYMENT_COMPLETED', registration_answer_code=answer_code)]
                    return [dict(repayments_data, status='LOAN_REPAYMENT_COMPLETED_NO_TOKEN')]
                except DeviceAPIError as error:
                    return [dict(repayments_data, status='LOAN_REPAYMENT_COMPLETED_UNLOCK_DISABLED'), handle_device_code_error(error)]
                except ConfigurationError as config_error:
                    return [dict(repayments_data, status='LOAN_REPAYMENT_COMPLETED_UNLOCK_DISABLED'), {
                        'success': False, 'status':
                        'CONFIGURATION_ERROR', 'error_type': str(config_error)
                    }]
            else:
                for rp in repayments:
                    rp.processed = True
            return [dict(repayments_data, status='LOAN_REPAYMENT_COMPLETED_UNLOCK_DISABLED')]

        if not can_auto_activate:
            return [cls.get_as_no_token(repayments_data)]

        hours_left = device.get_remaining_activation_time_in_hours()

        if positive(hours_left) or (device.Mode == DeviceMode.credit and device.credit_balance and positive(device.credit_balance)):
            try:
                activation_code = DeviceAPIService.sync_device_activation(device, repayments=repayments)
            except DeviceAPIError as error:
                return [handle_device_code_error(error)]

            if DeviceAPIService.device_requires_answer_code(device):
                return [dict(repayments_data, activation_answer_code=activation_code) ]
            return [cls.get_as_no_token(repayments_data)]

        return [
            cls.get_as_no_token(repayments_data),
            dict(
                repayments_data,
                status='NO_ACTIVATION_TIME_ON_DEVICE' if device.Mode == DeviceMode.time else 'NO_ACTIVATION_CREDIT_ON_DEVICE'
            )
        ]

    @staticmethod
    def get_as_no_token(answer):
        return dict(answer, status=answer['status']+'_NO_TOKEN')  

    @classmethod
    def _get_repayments_data(cls, contract, repayments):
        orm.flush()

        answer = cls._get_base_answer(contract, repayments)
        if contract.offer.type == OfferType.usage_based:
            return cls._get_usage_answer(answer, contract, repayments)
        answer.update(cls._get_time_bought_in_days_and_hours(repayments))
        answer.update(cls._get_expiration_data(contract))
        if contract.status == ContractStatus.completed:
            return dict(answer, status='LOAN_REPAYMENT_COMPLETED')

        answer.update(cls.get_money_progression_data(contract))
        if contract.offer.type != OfferType.time_based:
            answer.update(contract.get_weeks_progression_dict())
            return dict(answer, status='ACTIVATION_TIME_BOUGHT')
        monthly = contract.offer.is_monthly
        status = 'CONTRACT_PAYMENT_MADE' + ('_MONTHLY' if monthly else '')
        return dict(answer, status=status)

    @staticmethod
    def _get_base_answer(contract, repayments):
        transaction_ids = []
        for repayment in repayments:
            for reconciled_payment in repayment.reconciled_payments.filter(lambda rp: rp.linked_payment is not None):
                transaction_ids.append(reconciled_payment.linked_payment.Reference)
        return {
            'success': True,
            'amount_paid': round_if_exists(sum(r.amount_paid for r in repayments)),
            'device_serial': contract.linked_device.get_display_name() if contract.linked_device else '',
            'offer_name': contract.offer.name,
            'name': contract.client.person.name,
            'surname': contract.client.person.surname,
            'transaction_ids': ', '.join(set(transaction_ids)),
            'contract_reference': contract.reference
        }

    @staticmethod
    def _get_usage_answer(base, contract, repayments):    
        return dict(base, **{
            'status': 'CONTRACT_PAYMENT_MADE_USAGE_BASED',
            'credit_bought': round_if_exists(sum(r.get_credit_bought() for r in repayments)),
            'credit_unit': contract.offer.credit_unit,
        })

    @staticmethod
    def _get_time_bought_in_days_and_hours(repayments):
        total_days = sum(r.get_credit_bought() for r in repayments)
        return {
            'days_bought': int(total_days),
            'hours_bought': int((total_days*24) % 24),
            'days_bought_rounded': round(total_days),
        }

    @staticmethod
    def _get_expiration_data(contract):
        return {
            'expiration_time': contract.next_repayment_due_time,
            'expiration_time_day': contract.next_repayment_due_time.strftime('%d'),
            'expiration_time_month': contract.next_repayment_due_time.strftime('%m'),
            'expiration_time_year': contract.next_repayment_due_time.strftime('%Y')
        }

    @classmethod
    def reconcile_paid_lead_after_editing(cls, lead):
        reconciliations = lead.reconciled_payments.filter(lambda rp: (not rp.converse) and rp.type in ReconciledPaymentType.blocked_during_lead_editing).order_by(lambda r: (r.linked_payment is None, r.time))
        for reconciliation in reconciliations:
            payment = reconciliation.linked_payment
            account = reconciliation.payment_account
            amount = reconciliation.amount
            reconciliation.delete()
            cls.get_answer_for_lead(lead, payment, amount, account, check_awaiting_payment = False)
            orm.flush()
            
    @classmethod
    def reconcile_pending_payments_to_lead(cls, lead, check_status=True):
        reconciled_payments = lead.person.pending_reconciled_payments_filtered
        payments = orm.select(r.linked_payment for r in reconciled_payments)
        for payment in payments:
            orm.delete(r for r in payment.reconciled_payments.select() if r in reconciled_payments)
            cls.get_answer_for_lead(lead, payment, None, None, autoreconcile_from_client=False, check_awaiting_payment=check_status)
        amount_reconciliations = reconciled_payments.filter(lambda r: not r.linked_payment)
        grouped = orm.select((r.payment_account, sum(r.amount)) for r in amount_reconciliations)
        for account, amount in grouped:
            orm.delete(r for r in amount_reconciliations.filter(lambda r: r.payment_account == account))
            cls.get_answer_for_lead(lead, None, amount, account, autoreconcile_from_client=False, check_awaiting_payment=check_status)
            
    @classmethod
    def prepare_paid_lead_for_editing(cls, lead):
        payments = orm.select(r.linked_payment for r in lead.reconciled_payments if not r.converse)
        for payment in payments:
            orm.delete(r for r in payment.reconciled_payments.select() if r in lead.reconciled_payments)
            ReconciledPaymentService.create_reconciliation(
                lead=lead,
                type=ReconciledPaymentType.blocked_during_lead_editing,
                payment=payment
            )
        amount_reconciliations = lead.reconciled_payments.filter(lambda r: not r.linked_payment)
        grouped = orm.select((r.payment_account, sum(r.amount)) for r in amount_reconciliations)
        for account, amount in grouped:
            orm.delete(r for r in amount_reconciliations.filter(lambda r: r.payment_account == account))
            ReconciledPaymentService.create_reconciliation(
                lead=lead,
                type=ReconciledPaymentType.blocked_during_lead_editing,
                account=account,
                amount=amount
            )

    @staticmethod
    def get_money_progression_data(contract):
        maturity_date = contract.get_date_of_maturity_without_lateness()
        missing_downpayment = not SettingsService.get_setting('EnableContractPaymentsForReversedDownpayments') and not contract.downpayment_fully_paid
        minimum = contract.offer.registration_fee if missing_downpayment else contract.minimum_payment
        return {
            'contract_reference': contract.reference,
            'client_phone_number': contract.client.person.preferred_phone_number() or '',
            'device_serial': contract.linked_device.get_display_name() if contract.linked_device else '',
            'remaining_due': round_if_exists(contract.get_outstanding_balance()),
            'remaining_due_with_addons': round_if_exists(contract.get_outstanding_balance_with_addons()),
            'total_to_pay': round_if_exists(contract.get_total_value()),
            'total_to_pay_with_addons': round_if_exists(contract.get_total_value_with_addons(include_pending=True)),
            'paid_so_far': round_if_exists(contract.get_cumulative_amount_repaid()),
            'paid_so_far_with_addons': round_if_exists(contract.get_cumulative_amount_repaid_with_addons()),
            'pending_amount': round_if_exists(contract.pending_amount),
            'reference_payment': round_if_exists(contract.reference_price),
            'next_payment_price': round_if_exists(contract.next_payment_price()),
            'minimum_payment': round_if_exists(minimum),
            'expected_paid': round_if_exists(contract.get_expected_amount_repaid()) or 0,
            'amount_in_arrears': round_if_exists(contract.get_net_cumulative_amount_in_arrears()) or 0,
            'expected_maturity_day': maturity_date.strftime('%d') if maturity_date else '',
            'expected_maturity_month': maturity_date.strftime('%m') if maturity_date else '',
            'expected_maturity_year': maturity_date.strftime('%Y') if maturity_date else '',
        }

    @classmethod
    def _get_balance_insufficient_answer(cls, contract, success=False, payment=None):
        missing_downpayment = not SettingsService.get_setting('EnableContractPaymentsForReversedDownpayments') and not contract.downpayment_fully_paid
        minimum = contract.offer.registration_fee if missing_downpayment else contract.minimum_payment
        status = {
            'success': success,
            'status': 'BALANCE_INSUFFICIENT',
            'balance': round_if_exists(contract.pending_amount),
            'reference_payment': round_if_exists(contract.reference_price),
            'minimum_payment': round_if_exists(minimum),
            'pending_amount': round_if_exists(contract.pending_amount),
            'name': contract.client.person.name,
            'surname': contract.client.person.surname,
            'transaction_id': payment.Reference if payment else ''
        }
        if contract.offer.type == OfferType.loan:
            status['status'] = 'BALANCE_INSUFFICIENT_LOAN'
            status.update(contract.get_weeks_progression_dict())
            status.update(cls.get_money_progression_data(contract))
            status.update(cls._get_expiration_data(contract))
        return [status]


    @classmethod
    def _get_pending_payment_answer_for_paused_contract(cls, contract, payment):
        days_paid = round(contract.get_days_paid())
        days_to_pay = round(contract.get_days_to_pay())
        remaining_days_to_pay = round(contract.get_remaining_days_to_pay())
        weeks_paid = int(days_paid/7)
        days_paid = int(days_paid) - (weeks_paid * 7)
        weeks_to_pay = int(round(days_to_pay/7))
        remaining_weeks_to_pay = int(round(remaining_days_to_pay/7))
        return [{
            'success': True,
            'status': 'PAYMENT_FOR_PAUSED_CONTRACT_SETTING_ENABLED',
            'amount': round_if_exists(payment.Amount),
            'name': contract.client.person.name,
            'surname': contract.client.person.surname,
            'contract_reference': contract.reference,
            'device_serial': contract.linked_device.get_display_name() if contract.linked_device else '',
            'offer_name': contract.offer.name,
            'weeks_to_pay': weeks_to_pay,
            'days_to_pay': days_to_pay,
            'already_paid': round_if_exists(sum(r.amount_paid for r in contract.repayments)),
            'remaining_due': round_if_exists(contract.get_outstanding_balance()),
            'total_to_pay': round_if_exists(contract.get_total_value()),
            'paid_so_far': round_if_exists(contract.get_cumulative_amount_repaid()),
            'remaining_due-pending_amount': round_if_exists(contract.pending_amount),
            'next_payment_price': round_if_exists(contract.next_payment_price()),
            'expected_paid': round_if_exists(contract.get_expected_amount_repaid()) or 0,
            'amount_in_arrears': round_if_exists(contract.get_net_cumulative_amount_in_arrears()) or 0,
            'expiration_time_day': contract.next_repayment_due_time,
            'remaining_days_to_pay': remaining_days_to_pay,
            'remaining_weeks_to_pay': remaining_weeks_to_pay,
            'paid_so_far+pending_amount': round_if_exists(contract.get_cumulative_amount_repaid() + contract.pending_amount),
        }]
    # Client Name, Client Surname, Contract Reference, Device SN, Offer Name, Weeks to pay, Days to pay, 
    # Remaining weeks to pay, Remaining days to pay, Payment due day, Total price, Remaining due - pending amount, 
    # Already paid, Already paid + pending amount, next payment price, expected paid, Amount in arrears, pending amount
    @staticmethod
    def _error(status, data=None):
        return [dict({
            'success': False,
            'status': status,
        }, **(data or {}))]
