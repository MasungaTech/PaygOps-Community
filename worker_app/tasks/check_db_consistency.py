
from datetime import datetime

from pony.orm import db_session, desc, select

from core_system.users.models.user_model import User
from payg_loan_system.contracts.models.addons_model import ContractAddOn
from payg_loan_system.contracts.models.contract_event_model import \
    ContractEventType
from payg_loan_system.contracts.models.contract_model import Contract
from payg_loan_system.contracts.models.contract_status import ContractStatus
from payg_loan_system.contracts.models.reconciled_payment_model import \
    ReconciledPayment
from payg_loan_system.contracts.models.reconciled_payment_type import \
    ReconciledPaymentType
from payg_loan_system.contracts.models.repayment_discount_types import \
    ContractRepaymentDiscountTypes
from payg_loan_system.contracts.models.repayment_model import ContractRepayment
from payg_loan_system.contracts.services.contract_creation_service import \
    ContractCreationService
from payg_loan_system.contracts.services.contract_event_service import \
    ContractEventService
from payg_loan_system.contracts.services.contract_repayment_service import \
    ContractRepaymentService
from payg_loan_system.contracts.services.reconciled_payment_service import \
    ReconciledPaymentService
from payg_loan_system.devices.model.device_mode import DeviceMode
from payg_loan_system.offers.models import OfferType
from sales_system.leads.models.lead import Lead
from shared.logger.loggers import Error, LogAPI
from shared.services.settings_service import SettingsService
from stock_management_system.services.stock_movement_creation_service import \
    StockMovementCreationService
from stock_management_system.stock_status import StockStatus
from survey_system.models.survey_answer import SurveyAnswer
from worker_app.tasks.background_migrations_task import BackgroundMigrations
from worker_app.worker_app import worker_app


@worker_app.task
def check_db_consistency(*args, fix_issues=False, costly_checks=False, safe_fix=True, **kwargs):

    if costly_checks:
        try:
            with db_session:
                addons_ids = select(
                    (a.id, a.time_approved)
                    for a in ContractAddOn if a.contract.can_be_completed and
                    not a.contract.lump_sum and
                    a.contract.status == ContractStatus.active and a.onloan
                ).order_by(desc(2))
                total = addons_ids.count()
        except Exception as e:
            LogAPI.Error(f'Error checking add-ons: {e}')

        try:
            with db_session:
                i = 0
                affected = 0
                affected_list = []
                not_cancellations = 0
                not_cancellations_list = []
                for a_id, time in addons_ids:
                    a = ContractAddOn.get(id=a_id)
                    if i%1000 == 0 and i != 0:
                        print(f'Up to {time}: {i} processed,  {affected/i:.2%} affected so far ({not_cancellations/i:.2%} aren\'t cancellations)')
                    calculated = a.calculate_current_repayment_increase()
                    if abs(calculated-a.repayment_increase) > 5:
                        affected += 1
                        affected_list.append(a.reference)
                        if a.contract.add_ons.filter(lambda a: a.time_canceled is not None):
                            continue
                        not_cancellations += 1
                        not_cancellations_list.append(a.reference)
                    i+=1
                if affected:
                    LogAPI.Warning('CONSISTENCY ISSUE (NO FIX) - Add-ons with incorrect repayment_increase', other_data={'add_ons': affected_list, 'not_cancellations': not_cancellations_list, 'total': affected, 'not_cancellations_total': not_cancellations})
        except Exception as e:
            LogAPI.Error(f'Error checking add-ons: {e}')

    try:
        with db_session:
            contracts_with_addons_deposit_missing = Contract.select(lambda c: c.downpayment_fully_paid and c.loan_addons_downpayments != c.loan_addons_downpayments_paid)
            if contracts_with_addons_deposit_missing.count():
                LogAPI.Warning('CONSISTENCY ISSUE (NO FIX) - Contracts with addons downpayment missing', other_data=list(select(c.reference for c in contracts_with_addons_deposit_missing)))
    except Exception as e:
        LogAPI.Error(f'Error checking contracts with addons downpayment missing: {e}')

    try:
        with db_session:
            contracts_with_more_downpayment_than_value = Contract.select(lambda c: c.can_be_completed and not c.lump_sum and c.cached_total_downpayment >= c.queryable_total_value())
            if contracts_with_more_downpayment_than_value.count():
                LogAPI.Warning('CONSISTENCY ISSUE (NO FIX) - Contracts with more downpayment than value', other_data=list(select(c.reference for c in contracts_with_more_downpayment_than_value)))
    except Exception as e:
        LogAPI.Error(f'Error checking contracts with more downpayment than value: {e}')

    try:
        with db_session:
            contracts_without_downpayment = select(c for c in Contract if not c.repayments.filter(lambda r: r.discount_type == ContractRepaymentDiscountTypes.downpayment))
            if contracts_without_downpayment.count():
                LogAPI.Warning('CONSISTENCY ISSUE (NO FIX) - Contracts without downpayment', other_data=list(select(c.reference for c in contracts_without_downpayment)))
        # no fix, it will be fixed with downpayment reversal feature
    except Exception as e:
        LogAPI.Error(f'Error checking contracts without downpayment: {e}')

    try:
        with db_session:
            non_migrated_reconciliations = ReconciledPayment.select(lambda rp: rp.lead.contract and not rp.repayment and not rp.contract_pending_repayment and not rp.add_on and not rp.converse)
            if non_migrated_reconciliations.count():
                LogAPI.Warning('CONSISTENCY ISSUE - Installed Leads with reconciled payments not assigned to contract or add-ons', other_data=list(select(rp.lead.id for rp in non_migrated_reconciliations)))
            if fix_issues:
                for r in non_migrated_reconciliations:
                    contract = r.lead.contract
                    downpayment = contract.repayments.filter(lambda r: r.discount_type == ContractRepaymentDiscountTypes.downpayment).first()
                    if not downpayment and r.type == ReconciledPaymentType.initial_payment:
                        if not contract.contract_events.select(lambda e: e.type == ContractEventType.creation).get():
                            approver = contract.lead.decisionMaker if contract.lead else None
                            ContractEventService.create_contract_creation_event(contract, approver)
                        r.repayment = ContractRepaymentService.create_first_repayment_on_contract(contract, User.get_system_user())
                        LogAPI.Warning('Fixed Lead reconciliations not transferred for Contract (no downpayment) ['+contract.reference+']')
                    elif r.type == ReconciledPaymentType.blocked_during_lead_editing_reversal and not r.converse:
                        r.delete()
                        LogAPI.Warning('Fixed Lead reconciliations not linked to repayment (orphaned blocked during editing reversal removed) ['+contract.reference+']')
                    elif r.type == ReconciledPaymentType.blocked_during_lead_editing or r.type == ReconciledPaymentType.blocked_during_lead_editing_reversal:
                        if r.repayment:
                            r.type = ReconciledPayment.repayment
                            LogAPI.Warning('Fixed Lead reconciliations not linked to repayment (blocked during editing) ['+contract.reference+']')
                        else:
                            # payment = r.linked_payment
                            # account = r.payment_account
                            # amount = r.amount
                            # r.delete()
                            # flush()
                            # ReconciliationService.get_answer_for_contract(contract, payment, amount, account)
                            LogAPI.Warning('COULD NOT FIX Lead reconciliations not transferred for Contract (blocked during editing) ['+contract.reference+']')
                    elif r.type == ReconciledPaymentType.repayment_pending and not r.contract_pending_repayment:
                        if contract.status == ContractStatus.completed:
                            LogAPI.Warning('COULD NOT FIX Lead reconciliations not transferred for Contract (no repayment pending payment), contract is completed ['+contract.reference+']')
                        else:
                            r.contract_pending_repayment = contract
                            if r.converse:
                                r.converse.contract_pending_repayment = contract
                            else:
                                ContractRepaymentService.repay_and_reconcile(contract)
                            LogAPI.Warning('Fixed Lead reconciliations not transferred for Contract (no repayment pending contract) ['+contract.reference+']')
                    elif r.type == ReconciledPaymentType.repayment and not r.repayment:
                        # r.delete() # This can't be easily created and doesnt seem to exist so we remove
                        LogAPI.Warning('COULD NOT FIX Lead reconciliations not transferred for Contract (no repayment) ['+contract.reference+']')
                    elif r.type == ReconciledPaymentType.initial_payment:
                        r.repayment = downpayment
                        LogAPI.Warning('Fixed Lead reconciliations not transferred for Contract (no initial payment) ['+contract.reference+']')
                    else:
                        LogAPI.Warning('COULD NOT FIX Lead reconciliations not transferred for Contract (other issue) ['+contract.reference+'] ['+str(r.id)+']')
    except Exception as e:
        LogAPI.Error(f'Error checking non-migrated reconciliations: {e}')

    try:
        with db_session:
            installed_leads_with_wallets = Lead.select(lambda l: l.contract and l.payment_wallets)
            if installed_leads_with_wallets.count():
                LogAPI.Warning('CONSISTENCY ISSUE - Installed leads with wallets not trasferred', other_data=list(select(l.id for l in installed_leads_with_wallets)))
            if fix_issues or safe_fix:
                for lead in installed_leads_with_wallets:
                    ContractCreationService._link_payment_account(lead, lead.contract.client)
    except Exception as e:
        LogAPI.Error(f'Error checking installed leads with wallets not trasferred: {e}')

    try:
        with db_session:
            contracts_with_device_mode_not_synced = Contract.select(lambda c: c.status in [ContractStatus.active, ContractStatus.completed] and (
            (c.offer.type == OfferType.lump_sum and c.linked_device.Mode != DeviceMode.disabled) or
            (c.offer.type in OfferType.time_based and c.linked_device.Mode != DeviceMode.time) or
            (c.offer.type in OfferType.loan and c.status == ContractStatus.active and c.linked_device.Mode != DeviceMode.time) or
            (c.offer.type == OfferType.usage_based and c.linked_device.Mode != DeviceMode.credit)
            ))
            if contracts_with_device_mode_not_synced.count():
                LogAPI.Warning('CONSISTENCY ISSUE - Contracts Devices mode not synced', other_data=list(select(c.reference for c in contracts_with_device_mode_not_synced)))
            if fix_issues or safe_fix:
                for contract in contracts_with_device_mode_not_synced:
                    ContractRepaymentService.sync_device_status_from_contract(contract.linked_device, contract)
    except Exception as e:
        LogAPI.Error(f'Error checking contracts with device mode not synced: {e}')

    try:
        with db_session:
            contracts_devices_not_properly_moved = Contract.select(lambda c: c.status in [ContractStatus.active, ContractStatus.completed] and c.linked_device.stock_item.status != StockStatus.installed)
            if contracts_devices_not_properly_moved.count():
                LogAPI.Warning('CONSISTENCY ISSUE - Contracts Devices not properly moved', other_data=list(select(c.reference for c in contracts_devices_not_properly_moved)))
            if fix_issues or safe_fix:
                for contract in contracts_devices_not_properly_moved:
                    StockMovementCreationService.create(
                        contract.linked_device.stock_item,
                        StockStatus.installed,
                        user=User.get_system_user(),
                        destination_client=contract.client,
                        note="[Automatic] Registration",
                        manual=False
                    )
    except Exception as e:
        LogAPI.Error(f'Error checking contracts with device mode not synced: {e}')

    try:
        with db_session:
            leads_with_answers_not_transferred = select(sa.lead_answering.id for sa in SurveyAnswer if sa.lead_answering.contract and not sa.client_answering)[:]
        if len(leads_with_answers_not_transferred):
            LogAPI.Warning(f'CONSISTENCY ISSUE - Installed Leads with SurveyAnswers not linked to client', other_data=str(leads_with_answers_not_transferred))
        leads_with_answers_not_transferred = Lead.select(lambda l: l.id in leads_with_answers_not_transferred)
        if fix_issues or safe_fix:
            def link_survey_answer_to_client(lead):
                ContractCreationService._link_survey_answer_to_client(lead, lead.contract.client)
            BackgroundMigrations.chunk_executer(leads_with_answers_not_transferred, Lead, link_survey_answer_to_client, 'lead with not linked survey answers')
    except Exception as e:
        LogAPI.Error(f'Error checking leads with answers not transferred: {e}')

    try:
        with db_session:
            phantom_repayments = ContractRepayment.select(lambda r: not r.reconciled_payments and r.discount_type in ['', 'Downpayment'] and r.amount != 0 and not r.converse)
            if phantom_repayments.count():
                LogAPI.Warning(f'CONSISTENCY ISSUE - Phantom repayments', other_data=list(select(r.contract.reference for r in phantom_repayments)))
            if fix_issues:
                for rp in phantom_repayments:
                    rp.discount_type = ContractRepaymentDiscountTypes.special_discount
                    rp.note = 'Potential phantom repayment'
    except Exception as e:
        LogAPI.Error(f'Error checking phantom repayments: {e}')

    with db_session:
        max_difference = float(SettingsService.get_setting('MaxRoundingDiscount'))

    try:
        with db_session:
            active_contracts_paid = Contract.select(lambda c: c.status not in [ContractStatus.completed, ContractStatus.overpaid] and c.can_be_completed and (float(abs(c.queryable_balance())) < max_difference or float(c.cached_total_value-c.cached_cumulative_amount_repaid) < max_difference))
            if active_contracts_paid.count():
                LogAPI.Warning(f'CONSISTENCY ISSUE - Found not completed contracts paid', other_data=list(select(c.reference for c in active_contracts_paid)))
            if fix_issues or safe_fix:
                def finish_contract(contract):
                    now = datetime.now()
                    difference = contract.get_outstanding_balance()
                    if difference < max_difference:
                        ContractRepaymentService.finish_contract(contract, now)
                BackgroundMigrations.chunk_executer(active_contracts_paid, Contract, finish_contract, 'complete paid contracts')
    except Exception as e:
        LogAPI.Error(f'Error checking active contracts paid: {e}')

    try:
        with db_session:
            completed_contracts_without_discount = Contract.select(lambda c: c.status == ContractStatus.completed and ((float(abs(c.queryable_balance())) < max_difference and float(abs(c.queryable_balance())) >= 0.01) or (float(c.cached_total_value-c.cached_cumulative_amount_repaid) < max_difference and float(c.cached_total_value-c.cached_cumulative_amount_repaid) >= 0.01)))
            if completed_contracts_without_discount.count():
                LogAPI.Warning(f'CONSISTENCY ISSUE - Found completed contracts without discount', other_data=list(select(c.reference for c in completed_contracts_without_discount)))
            if fix_issues:
                def task(c):
                    difference = c.get_outstanding_balance()
                    if difference and difference < max_difference:
                        ContractRepaymentService._create_repayment_object(
                            contract=c,
                            time=datetime.now(),
                            expected_time=c.next_repayment_due_time,
                            next_repayment_due_time=c.next_repayment_due_time,
                            amount=difference,
                            amount_discounted=difference,
                            hours_late=0,
                            amount_late=0,
                            discount_type=ContractRepaymentDiscountTypes.rounding,
                        )
                BackgroundMigrations.chunk_executer(completed_contracts_without_discount, Contract, task, 'add discount to completed contracts')
    except Exception as e:
        LogAPI.Error(f'Error checking completed contracts without discount: {e}')

    try:
        with db_session:
            completed_contracts_not_paid = Contract.select(lambda c: c.status == ContractStatus.completed and (float(abs(c.queryable_balance())) >= max_difference or float(c.cached_total_value-c.cached_cumulative_amount_repaid) >= max_difference))
            if completed_contracts_not_paid.count():
                LogAPI.Warning(f'CONSISTENCY ISSUE - Found completed contracts not paid', other_data=list(select(c.reference for c in completed_contracts_not_paid)))
            if fix_issues or safe_fix:
                for contract in completed_contracts_not_paid:
                    try:
                        if contract.get_outstanding_balance() >= max_difference and contract.status == ContractStatus.completed:
                            if not contract.linked_device:
                                raise Error
                            ContractRepaymentService.reactivate_contract(contract, sync_device=False)
                    except Error: # Already has an active contract and multiple active contracts is disabled
                        LogAPI.Warning(f'Failed fix: reactivate contract that is not completely paid', other_data={'contract': contract.reference})
    except Exception as e:
        LogAPI.Error(f'Error checking completed contracts not paid: {e}')

    try:
        with db_session:
            lump_sum_contracts_not_paid = Contract.select(lambda c: c.lump_sum and c.queryable_balance_lump_sum() != 0)
            if lump_sum_contracts_not_paid.count():
                LogAPI.Warning(f'CONSISTENCY ISSUE - Found lump sum contracts not paid', other_data=list(select(c.reference for c in lump_sum_contracts_not_paid)))
    except Exception as e:
        LogAPI.Error(f'Error checking lump sum contracts not paid: {e}')

    try:
        # We also do the survey answer fixing
        from worker_app.tasks.fix_first_last_answers import \
            fix_answer_person_first_last
        fix_answer_person_first_last()
    except Exception as e:
        LogAPI.Error(f'Error fixing first last answers: {e}')
        

def fix_orphaned_repayment(rp):
    contract = rp.contract
    amount = rp.amount_paid
    good_wallets = select(w for w in contract.client.payment_wallets)[:]
    alternative_wallets = []
    previous_repayments = contract.repayments.filter(lambda r: (not r.discount_type or r.discount_type == ContractRepaymentDiscountTypes.downpayment) and r.id < rp.id)
    previous_repayments = previous_repayments.order_by(lambda r: desc(r.id)).limit(10)
    for p in previous_repayments:
        for r in p.reconciled_payments:
            if r.payment_account not in alternative_wallets:
                alternative_wallets.append(r.payment_account)

    for wallet in good_wallets:
        if wallet.balance >= amount:
            create_reconciled_payment(rp, wallet)
            return 'Wallet Balance (Good)'

    for wallet in alternative_wallets:
        if wallet.balance >= amount:
            create_reconciled_payment(rp,wallet)
            return 'Wallet Balance'

    return 'NOT FIXED'

def create_reconciled_payment(repayment, wallet):
    r = ReconciledPaymentService._create_reconciled_payment_object(
        time=repayment.time,
        type=ReconciledPaymentType.repayment,
        account=wallet,
        amount=repayment.amount_paid,
    )
    r.repayment = repayment