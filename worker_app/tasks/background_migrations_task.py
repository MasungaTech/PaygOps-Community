import json
import math
import os
from datetime import datetime, timedelta
from decimal import Decimal
from email.utils import parseaddr

from PIL import Image, ImageDraw, ImageFont
from pony import orm
from pony.orm import commit, db_session, flush, select
from requests import HTTPError

import config
import shared.migrations.commands.migrate as migration_commands
from accounting_system.accounting_db import Expense, accounting_db
from constants import ENTITIES_OLD_ID_OFFSET
from core_system.client.models import Client
from core_system.core_entities import db as core_db
from core_system.operational_entities.models import OperationalEntity
from core_system.person.models.person_model import Person
from core_system.phone_numbers.services.add_phone_number_service import \
    AddPhoneNumberService
from core_system.users.models.user_model import User
from data_system.analytical_db.analytical_db import analytical_db
from data_system.analytical_db.services.model_update_service import \
    ModelUpdateService
from messages_system.models.sms_db import IncomingSMS, OutgoingSMS
from payg_loan_system.contracts.models.addon_bundle_model import \
    ContractAddOnBundle
from payg_loan_system.contracts.models.addons_model import (AddOnType,
                                                            ContractAddOn)
from payg_loan_system.contracts.models.contract_event_model import (
    ContractEvent, ContractEventType)
from payg_loan_system.contracts.models.contract_model import Contract
from payg_loan_system.contracts.models.contract_status import ContractStatus
from payg_loan_system.contracts.models.reconciled_payment_model import \
    ReconciledPayment
from payg_loan_system.contracts.models.reconciled_payment_type import \
    ReconciledPaymentType
from payg_loan_system.contracts.models.repayment_discount_types import \
    ContractRepaymentDiscountTypes
from payg_loan_system.contracts.models.repayment_model import ContractRepayment
from payg_loan_system.contracts.services.addon_service import AddonService
from payg_loan_system.contracts.services.contract_creation_service import \
    ContractCreationService
from payg_loan_system.contracts.services.contract_event_service import \
    ContractEventService
from payg_loan_system.contracts.services.contract_repayment_service import \
    ContractRepaymentService
from payg_loan_system.contracts.services.reconciled_payment_service import \
    ReconciledPaymentService
from payg_loan_system.devices.device_api.device_api_request_service import \
    DeviceAPIRequestService
from payg_loan_system.devices.model.device import Device
from payg_loan_system.devices.model.device_metrics_model import Metric
from payg_loan_system.devices.model.product_sub_type import ProductSubType
from payg_loan_system.offers.models import Offer
from payg_loan_system.payments.models.payment import Payment
from payg_loan_system.payments.models.wallet import (PaymentWallet,
                                                     PaymentWalletType)
from payg_loan_system.payments.services.reconciliation_service import \
    ReconciliationService
from payg_loan_system.reversed_payments.models import ReversedPayment
from sales_system.leads.models.lead import Lead
from sales_system.leads.models.status_category import DECISION_MADE_CATEGORIES
from shared.api_helpers.client_helpers.uuid_generation_helpers import \
    generate_uuid
from shared.file_upload.model import StoredFile, StoredFileType
from shared.file_upload.services.stored_file_service import StoredFileService
from shared.helpers.chunk_executer import isolated_chunk_executer
from shared.helpers.date_helper import timedelta_to_hours
from shared.helpers.db_helpers import get_float_columns, searchable_text
from shared.logger.loggers import Error, LogAPI, LogService
from shared.model.billing import Bill
from shared.services.settings_service import SettingsService
from stock_management_system.models import StockItem, StockMovement
from stock_management_system.services.stock_movement_creation_service import \
    StockMovementCreationService
from stock_management_system.stock_status import StockStatus
from survey_system.models.answer import Answer
from survey_system.models.forms import Form, FormVersion
from survey_system.models.question_choice import QuestionChoice
from survey_system.models.survey_answer import SurveyAnswer
from worker_app.worker_app import worker_app
from payg_loan_system.devices.device_api.device_api_request_service import DeviceAPIError
from payg_loan_system.contracts.models.contract_event_model import ContractEvent, ContractEventType
from payg_loan_system.contracts.models.addons_model import AddOnType


def sign(x):
    return 1 if x > 0 else -1

class BackgroundMigrations:

    @classmethod
    @db_session
    def remove_lumpsump_contract_events(cls):
        # Find all contract events of type Value Change or Duration Change
        events = select(e.id for e in ContractEvent if e.type in [ContractEventType.value_change, ContractEventType.duration_change])
        def fix_event(event):
            for addon in event.addons:
                if addon.offer_version.offer.type == AddOnType.lump_sum:
                    event.delete()
                    break
        isolated_chunk_executer(events[:], ContractEvent, fix_event, action_name='Remove Lump-Sum Contract Events')

    @classmethod
    @db_session
    def fix_missing_decision(cls):
        leads = orm.select(
            l.id for l in Lead if not l.decision and l.status.category in DECISION_MADE_CATEGORIES)
        if leads:
            print(f'Fixing {leads.count()} leads without decision')
            def fix_decision(r):
                r.decision = True
            isolated_chunk_executer(leads[:], Lead,
                fix_decision, action_name='Fix lead decision')

    @classmethod
    @db_session
    def fix_inconsistent_converse(cls):
        recons = orm.select(
            r.id for r in ReconciledPayment if r.converse and (
                r.linked_payment and not r.converse.linked_payment
                or r.lead and not r.converse.lead
            ))
        if recons:
            print(f'Fixing {recons.count()} reconciled payments with converse and inconsistencies')
            def fix_recon(r):
                r.converse.linked_payment = r.linked_payment
                r.converse.lead = r.lead
            isolated_chunk_executer(recons[:], ReconciledPayment,
                fix_recon, action_name='Fix inconsistnecies in converse reconciliations')

    @classmethod
    @db_session
    def restore_real_last_status_change_date(cls):
        leads = Lead.select(lambda l: 
            (l.statusUpdate-max(sc.date for sc in l.status_changes_history)) > timedelta(seconds=5) or
            (l.statusUpdate-max(sc.date for sc in l.status_changes_history)) < timedelta(seconds=-5)
        )
        def task(l):
            l.statusUpdate = max(sc.date for sc in l.status_changes_history)
        cls.chunk_executer(leads, Lead, task, 'restore real last status change date')
        background_migration_task.delay("update_all_in_model_in_analytical_db", model="Leads")

    @classmethod
    @db_session
    def fix_device_not_properly_moved_in_swaps(cls):
        contracts_not_installed = Contract.select(
            lambda c: c.linked_device.stock_item.status != StockStatus.installed and orm.exists(
                c.linked_device.contract_event_new_device.select()
            )
        )
        print(f'Found {contracts_not_installed.count()} contracts with devices not in installed status')
        for contract in contracts_not_installed:
            print(f'Fixing {contract.linked_device.composed_serial}')
            event = contract.contract_events.select(
                lambda e: e.contract == contract and e.type == ContractEventType.device_swap and e.new_device == contract.linked_device
            ).get()
            StockMovementCreationService.create(
                contract.linked_device.stock_item,
                StockStatus.installed,
                user=event.approver,
                destination_client=contract.client,
                note="[Automatic] Device Swap",
                manual=False
            )
        devices_not_uninstalled = Device.select(
            lambda d: d.stock_item.status == StockStatus.installed and not d.contract and orm.exists(
                d.contract_event_old_device.select()
            )
        )
        print(f'Found {devices_not_uninstalled.count()} devices in installed status without a contract')
        for device in devices_not_uninstalled:
            print(f'Fixing {device.composed_serial}')
            event = device.contract_event_old_device.select(
                lambda e: e.type == ContractEventType.device_swap
            ).order_by(lambda e: orm.desc(e.time)).first()
            StockMovementCreationService.create(
                device.stock_item,
                StockStatus.with_user,
                user=event.approver,
                destination_user=event.approver,
                note="[Automatic] Device Swap",
                manual=False
            )

    @classmethod
    @db_session
    def sync_existing_devices_sub_type(cls):
        for api_name in SettingsService.get_setting('AllDeviceAPIS'):
            handler = DeviceAPIRequestService.get_device_api_helper(api_name)
            devices = Device.select(lambda d: d.type == api_name)
            def sync_sub_type(d):
                try:
                    device_data = handler.get_device_data(d.SerialNumber)
                    name = device_data.get('model', '')
                    sub_type = ProductSubType.get(name=name, device_type=api_name) if name else None
                    if not sub_type and name:
                        sub_type = ProductSubType(name=name, device_type=api_name)
                    d.product_sub_type = sub_type
                except (HTTPError, DeviceAPIError) as error:
                    LogAPI.FatalNoRequest(error)
            cls.chunk_executer(devices, Device, sync_sub_type, f"Sync devices sub-type of type {api_name}")

    @classmethod
    @db_session
    def remove_empty_text_option(cls):
        QuestionChoice.select(lambda c: orm.exists(c.text.filter(lambda ct: ct.value_text == ''))).delete(bulk=True)

    @classmethod
    @db_session
    def update_all_total_downpayment(cls):
        objs = Contract.select(lambda c: not c.cached_cumulative_credit_bought)
        def task(c):
            c.cached_cumulative_credit_bought = c.get_credits_bought(cached=False)
        cls.chunk_executer(objs, Contract, task, 'cached totalcredit bought update')
    
    @classmethod
    @db_session
    def lock_all_registered_leads(cls):
        leads = Lead.select(lambda l: not l.offer_editing_locked and l.installed)
        for l in leads: l.offer_editing_locked = True

    @classmethod
    def fix_hours_late_non_forgiving_offers(cls):
        with db_session:
            contracts_ids = select(c.id for c in Contract if not c.offer.forgive_lateness)[:]
        
        total = len(contracts_ids)
        done = 0
        print(f'Fixing {total} contracts with non forgiving offers')
        for contract_id in contracts_ids:
            with db_session:
                contract = Contract.get(id=contract_id)
                last_time = None
                for repayment in contract.repayments.select().order_by(ContractRepayment.time):
                    if last_time:
                        repayment.after_update = lambda: None
                        expected_date = max(last_time, repayment.expected_time)
                        hours_late = math.ceil(timedelta_to_hours(repayment.time - expected_date)*Decimal('10000'))/Decimal('10000')
                        amount_late = contract.get_value_of_credit(hours_late/Decimal('24'), time=repayment.time)
                        if abs(hours_late) > 10**10:
                            LogAPI.Warning('Hours late more than allowed in Database')
                            hours_late = round(sign(hours_late)*9.9**10, 2)
                        if abs(amount_late) > 10**10:
                            LogAPI.Warning('amount_late more than allowed in Database')
                            amount_late = round(sign(amount_late)*9.9**10, 2)
                        repayment.hours_late = hours_late
                        repayment.amount_late = amount_late
                    last_time = repayment.time
                # contract.update_cached_data(repayment_created=True)
            done += 1
            if done % 100 == 0:
                print(f'Fixed {done}/{total} ({done/total*100:.2f}%) contracts with non forgiving offers')
            

    @classmethod
    @db_session
    def add_contact_phone_to_phone_numbers(cls):
        persons = Person.select(lambda p: p.contactPhone and p.contactPhone not in p.phoneNumbers)
        for p in persons:
            p.phoneNumbers.add(p.contactPhone)


    @classmethod
    @db_session
    def link_first_downpayment_to_lead(cls):
        recons = ReconciledPayment.select(lambda r: not r.lead and r.type == ReconciledPaymentType.initial_payment and r.time == r.repayment.contract.start_time)
        for r in recons:
            if r.linked_payment: r.linked_payment.check_coherence_flag = False
            r.lead = r.repayment.contract.lead
            # if r.linked_payment: r.linked_payment.check_coherence_flag = True


    @classmethod
    @db_session
    def reverse_contracts_with_phantom_repayments_and_status(cls, status, note):
        repayments = ContractRepayment.select(lambda r: not r.reconciled_payments and r.discount_type in ['', 'Downpayment'] and r.amount != 0)
        repayments = repayments.filter(lambda r: r.contract.status == status and not r.converse)
        print(f'Reversing {repayments.count()} phantom repayments on contracts with status {status}')
        for r in repayments:
            try:
                ContractRepaymentService.reverse_repayment(r, note=note, reconcile_to_client=True)
            except Error:
                LogAPI.Warning(f'Failed to reverse phantom repayment', other_data={'contract': r.contract.reference, 'repayment': r.id})
                

    @classmethod
    @db_session      
    def clean_survey_answers_for_lead_and_form(cls, lead_id=None, form_id=None):
        if not lead_id or not form_id:
            raise Exception('Missing lead_id or form_id')
        forms = SurveyAnswer.select(
            lambda sa: sa.lead_answering.id == lead_id and sa.surveyAnswered.id == form_id and not sa.is_last_answer and not sa.is_first_answer
        )
        forms.delete(bulk=True)


    @classmethod
    @db_session
    def get_list_of_contracts_with_phantom_repayments(cls):
        repayments = ContractRepayment.select(lambda r: not r.reconciled_payments and r.discount_type in ['', 'Downpayment'] and r.amount != 0 and not r.converse)
        affected_contracts = select(r.contract for r in repayments)
        value_per_status = select((r.contract.status, float(orm.sum(r.amount))) for r in repayments)
        statuses = select((c.status, orm.count(c)) for c in affected_contracts)
        if affected_contracts:
            LogAPI.Warning(f'Found contracts with phantom repayments', other_data={
                'total_repayments': repayments.count(),
                'contract_list': list(select(c.reference for c in affected_contracts)),
                'total_contracts': affected_contracts.count(),
                'statuses': list(statuses),
                'value_per_status': list(value_per_status)
            })

    @classmethod
    @db_session
    def get_list_of_contracts_with_neg_delays_and_expected_paid_adjustment(cls):
        neg_delay_contracts = set(select(r.contract.reference for r in ContractRepayment if r.delay_given_in_hours < 0)[:])
        expected_paid_contracts = set(select(e.contract.reference for e in ContractEvent if e.type == ContractEventType.expected_paid_change)[:])
        affected_contracts = neg_delay_contracts.intersection(expected_paid_contracts)
        if affected_contracts:
            LogAPI.Warning(f'Found contracts with expected paid change and negative delays', other_data=list(affected_contracts))

    
    @classmethod
    def remove_extra_reconciliations_to_downpayments(cls):
        with db_session:
            downpayments = ContractRepayment.select(lambda r: r.discount_type == ContractRepaymentDiscountTypes.downpayment and r.amount_paid < r.total_reconciled)
            print(f'Fixing {downpayments.count()} downpayments with more reconciled than paid')
            for downpayment in downpayments:
                total_reconciled = 0
                for rp in downpayment.reconciled_payments.select().order_by(lambda rp: rp.time):
                    if total_reconciled >= downpayment.amount_paid:
                        payment = rp.linked_payment
                        rp.delete()
                        if payment:
                            payment.payment_or_reconciled_changed()
                    else:
                        total_reconciled += rp.amount

    @classmethod
    @db_session
    def update_all_addons_cached_properties(cls):
        addons = ContractAddOn.select()
        cls.chunk_executer(addons, ContractAddOn, lambda a: a.update_cached_properties(), 'Update cached properties')

    @classmethod
    def update_addons_without_lead_in_analytical_db(cls):
        with db_session:
            to_update_ids = select(a.id for a in analytical_db.AddOns if not a.lead_id)[:]
        ModelUpdateService.update_model_objects(analytical_db.AddOns, [], [], to_update_ids)
    
    @classmethod
    def update_all_in_model_in_analytical_db(cls, model):
        with db_session:
            to_update_ids = select(o.id for o in getattr(analytical_db, model))[:]
        ModelUpdateService.update_model_objects(getattr(analytical_db, model), [], [], to_update_ids)

    @classmethod
    def update_all_leads_in_analytical_db(cls):
        with db_session:
            to_update_ids = select(l.id for l in Lead)[:]
        ModelUpdateService.update_model_objects(analytical_db.Leads, [], [], to_update_ids)

    @classmethod
    @db_session
    def reverse_blocked_amount_for_installed_lead(cls):
        rps = ReconciledPayment.select(lambda rp: rp.type == ReconciledPaymentType.blocked_during_lead_editing and rp.lead.contract)
        print(f'Reverting {rps.count()} reconciliations with blocked money in installed leads')
        for rp in rps:
            ReconciledPaymentService.revert(rp)

    @classmethod
    @db_session
    def restore_deleted_reconciliations_of_reversed_payments(cls):
        reversed_payments = ReversedPayment.select(lambda rp: rp.handled and not rp.reconciled_payment and rp.payment)
        print(f'Fixing {reversed_payments.count()} reversed payments')
        for rp in reversed_payments:
            if rp.payment.PaymentWallet.get_balance() >= rp.payment.Amount:
                ReconciledPayment(
                    time=datetime.now(),
                    amount=rp.payment.Amount,
                    payment_account=rp.payment.PaymentWallet,
                    type=ReconciledPaymentType.payment_reversal,
                    reversed_payment=rp
                )

    @classmethod
    @db_session
    def revert_reconciliations_to_cancelled_addons(cls):
        for addon in ContractAddOn.select(lambda a: a.time_canceled and a.already_paid):
            LogAPI.Warning(f'Addon [{addon.reference}] was cancelled but had money on it, reversing reconciliations')
            for reconciled in addon.reconciled_payments.select(lambda r: not r.converse):
                ReconciledPaymentService.revert(reconciled, time=datetime.now())

    @classmethod
    @db_session
    def update_outdated_bundle_availability(cls):
        for bundle in ContractAddOnBundle.select():
            bundle.update_cached_data()

    @classmethod
    @db_session
    def fix_devices_without_first_movement(cls):
        items = StockItem.select(lambda i: not i.last_movement)
        for item in items:
            StockMovement(
                stock_item=item,
                date=datetime.now(),
                destination_status=StockStatus.orphaned,
                product_sub_type=item.device.product_sub_type.id if item.device and item.device.product_sub_type else None
            )

    @classmethod
    @db_session
    def fix_downpayments_not_allocated_to_addons(cls):
        affected_reconciliations = ReconciledPayment.select(lambda rp: (
            rp.repayment.amount != rp.amount and rp.repayment.discount_type == ReconciledPaymentType.initial_payment and
            rp.amount - rp.repayment.amount == orm.sum(a.total_amount for a in rp.lead.lump_sum_addons) and not rp.converse
        ))
        for rp in affected_reconciliations:
            rp.amount = rp.repayment.amount
            flush()
            ReconciliationService.get_answer_for_addons(
                rp.repayment.contract,
                rp.lead.lump_sum_addons,
                rp.linked_payment,
                rp.amount,
                rp.payment_account
            )

    @classmethod
    @db_session
    def clean_allocated_device_for_installed_leads(cls):
        for lead in Lead.select(lambda l: l.installed and l.allocated_device):
            lead.allocated_device = None

    @classmethod
    def chunk_executer(cls, objects, base_object, function, action_name='', chunk_size=100):
        ids = orm.select(p.id for p in objects)[:]
        count = len(ids)
        initial_count = count
        CHUNK_SIZE = chunk_size
        if count > 0:
            print(f'{count} to process for {action_name}')
            for ids_chunk in cls.chunker(ids, CHUNK_SIZE):
                objs = orm.select(p for p in base_object if p.id in ids_chunk)
                try:
                    for obj in objs:
                        function(obj)
                except Exception as e:
                    for obj in objs:
                        function(obj)
                count = count-CHUNK_SIZE
                orm.commit()
                print(f'{count}/{initial_count} left to process for {action_name}')


    @classmethod
    @db_session
    def fill_cached_data(cls, entity=None):
        # FormVersions (Surveys)
        if not entity or entity == 'forms':
            sas = orm.select(sa for sa in FormVersion)
            cls.chunk_executer(sas, FormVersion, lambda l: l.cached_data_get('mobile_object'), 'surveys (form version) cached data filling')
        # Leads
        if not entity or entity == 'leads':
            leads = orm.select(l for l in Lead)
            cls.chunk_executer(leads, Lead, lambda l: l.cached_data_get('reference_price'), 'lead cached data filling')
        # Survey Answers
        if not entity or entity == 'answers':
            sas = orm.select(sa for sa in SurveyAnswer)
            cls.chunk_executer(sas, SurveyAnswer, lambda l: l.cached_data_get('mobile_object'), 'survey answers cached data filling')
        # Device
        if not entity or entity == 'devices':
            sas = orm.select(sa for sa in Device)
            cls.chunk_executer(sas, Device, lambda l: l.cached_data_get('mobile_object'), 'devices cached data filling')
        

    @classmethod
    @db_session
    def populate_bill_with_aggregated_values(cls):
        bills = Bill.select(lambda b: not b.aggregated_billed_items)
        print(f'Populating {bills.count()} bills without aggregated billed items')
        for bill in bills:
            for billed_item in bill.billed_items:
                if billed_item.contract: person = billed_item.contract.client.person
                elif billed_item.add_on.lead: person = billed_item.add_on.lead.person
                else: person = billed_item.add_on.contract.client.person
                aggregated_billed_item = BillingService.get_or_create_aggregated_billable_item(bill, person, billed_item.type)
                billed_item.aggregated_billed_item = aggregated_billed_item
                BillingService.update_aggregated_billable_item_value_and_tier(aggregated_billed_item, billed_item.value)
        

    @classmethod
    @db_session
    def remove_0_value_reconciliations(cls):
        wrong_reconciliations = ReconciledPayment.select(lambda r: 
            r.amount == 0 and r.type != 'Manual Adjustment' and
            not r.converse and r.repayment and
            r.repayment.amount == sum(rc.amount for rc in r.repayment.reconciled_payments)
        )
        print(f'Removing {wrong_reconciliations.count()} wrong reconciliations that are not manual adjustments but have value 0')
        for recon in wrong_reconciliations:
            recon.delete()


    @classmethod
    @db_session
    def fill_searchable_name(cls):
        Person.before_update = lambda p: None
        persons = orm.select(p for p in Person if not p.searchable_name)
        count = persons.count()
        CHUNK_SIZE = 100
        if count > 0:
            LogService.Warning(f'[{count}] persons to make searchable. ')
            person_ids = orm.select(p.id for p in persons)[:]
            for person_ids_chunk in cls.chunker(person_ids, CHUNK_SIZE):
                persons = orm.select(p for p in Person if p.id in person_ids_chunk)
                try:
                    for person in persons:
                        person.searchable_name = searchable_text(person.name + ' ' + person.surname)
                    orm.commit()
                except Exception as e:
                    for person in persons:
                        person.searchable_name = searchable_text(person.name + ' ' + person.surname)
                    orm.commit()
                count = count-CHUNK_SIZE
                print(f'{count} persons left to make searchable.')

    @classmethod
    def update_modified_date_addons(cls):
        with db_session:
            to_update_ids = [a.id for a in ContractAddOn.select(lambda a: a.offer_version.downpayment is not None)]
        ModelUpdateService.update_model_objects(analytical_db.AddOns, [], [], to_update_ids)
    
    @classmethod
    def populate_overpaid_amount(cls):
        with db_session:
            to_update_client_ids = [c.id for c in Client.select(lambda c: c.person.reconciled_payments)]
        ModelUpdateService.update_model_objects(analytical_db.Clients, [],[], to_update_client_ids)
    
    @classmethod
    def generate_image_file(cls, text, uuid):
        font_size = int(round(1200/len(text)))
        image = Image.new("RGB", (600,300), (255,255,255))
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(config.WEB_STATIC_PATH+"/font/Fasthand-Regular.ttf", size=font_size)
        draw.text((10, 120-int(font_size/2)), text, (0,0,0), font=font)
        img_resized = image.resize((300,150), Image.LANCZOS)
        img_resized.save(os.path.join(config.CONTENT_PATH+'pictures', uuid+'.jpg'))
        img_resized.save(os.path.join(config.CONTENT_PATH+'pictures', uuid+'_t.jpg'))

    @classmethod
    @db_session
    def fix_signatures(cls):
        bad_signatures_ids = select(s.id for s in Answer if s.value_stored_file.uuid == 'my-uuid' or '_placeholder' in s.value_stored_file.uuid)[:]
        total = len(bad_signatures_ids)
        done = 0
        for bad_signatures_ids_chunk in cls.chunker(bad_signatures_ids, 100):
            bad_signatures = select(s for s in Answer if s.id in bad_signatures_ids_chunk)
            print(f'Processing signatures: {done}/{total}')
            done += 100
            for sign in bad_signatures:
                person_name = sign.surveyAnswer.person_answering.name.title()+' '+sign.surveyAnswer.person_answering.surname[0].title()+'.'
                uuid = generate_uuid()+'_placeholder'
                file_object = StoredFileService.create_without_file(
                    type=StoredFileType.PICTURE,
                    uuid=uuid
                )
                cls.generate_image_file(person_name, uuid)
                file_object.available = True
                sign.value_stored_file = file_object
            orm.commit()


    @classmethod
    def chunker(cls, seq, size):
        return (seq[pos:pos + size] for pos in range(0, len(seq), size))

    @classmethod
    @db_session
    def populate_clients_eligible_for_new_contract(cls):

        clients = Client.select(lambda c: c.active_contracts.count() == 0 and c.person.lead.filter(lambda l: not l.contract and not l.discarded).count() == 0)
        print(f'Populating {clients.count()} eligible for new contract')
        for client in clients:
            client.eligible_for_new_contract = True

    @classmethod
    @db_session
    def fix_leads_with_wrong_maximum_pending(cls):

        total_contracts_new_payment = 0

        wrong_neg_downpayment_leads = Lead.select(lambda l: (l.already_paid or l.contract) and l.offer_editing_locked and l.addons.filter(lambda a: a.downpayment < 0 and a.downpayment != a.already_paid))
        print(f'Fixing {wrong_neg_downpayment_leads.count()} leads/contracts with wrong negative downpayment addons')
        for lead in wrong_neg_downpayment_leads:
            try:
                if lead.contract:
                    print(f'Fixing contract {lead.contract.reference}')
                    if lead.contract.get_cumulative_amount_repaid_without_deposit() < 0:
                        LogAPI.Warning(f'Contract [{lead.contract.reference}] has negative paid without downpayment, need to be cancelled')
                        continue
                    if lead.contract.status == ContractStatus.defaulted:
                        print('is defaulted')
                        lead.contract.allow_defaulted = True # this is just a patch for the bugfix
                    rc = lead.reconciled_payments.select().first()
                    if not rc or lead.already_paid < lead.downpayment: # this can't be fixed automatically
                        LogAPI.Warning(f'Contract [{lead.contract.reference}] has unfixed negative deposit add-ons (probably has a negative total downpayment or unpaid downpayment)')
                        continue
                    neg_down_addons = lead.addons.filter(lambda a: a.downpayment < 0 and a.downpayment != a.already_paid)
                    total_made_available = 0
                    payment = rc.linked_payment
                    account = rc.payment_account
                    for addon in neg_down_addons:
                        new_rc = ReconciledPaymentService.create_reconciliation(
                            lead=lead,
                            addon=addon,
                            type=ReconciledPaymentType.addon,
                            payment=payment,
                            amount=rc.amount,
                            account=account
                        )
                        total_made_available -= new_rc.amount
                    for addon in lead.lump_sum_addons.filter(lambda a: not a.paid and not a.free).order_by(lambda l: l.time_created):
                        recon = ReconciledPaymentService.create_reconciliation(
                            lead=lead,
                            addon=addon,
                            type=ReconciledPaymentType.addon,
                            payment=payment,
                            account=account,
                            amount=total_made_available)
                        total_made_available = total_made_available-recon.amount if total_made_available else total_made_available
                    for addon in lead.loan_addons.filter(lambda a: a.already_paid < a.downpayment).order_by(lambda l: l.time_created):
                        recon = ReconciledPaymentService.create_reconciliation(
                            lead=lead,
                            addon=addon,
                            type=ReconciledPaymentType.addon,
                            payment=payment,
                            account=account,
                            amount=total_made_available)
                        total_made_available = total_made_available-recon.amount if total_made_available else total_made_available
                        commit()
                    if total_made_available:
                        ReconciliationService.get_answer_for_contract(lead.contract, payment=rc.linked_payment, amount=total_made_available, account=rc.payment_account)
                        total_contracts_new_payment += 1
                    commit()
                    continue
            
                print(f'Fixing lead {lead.id}')
                ReconciliationService.prepare_paid_lead_for_editing(lead)
                if lead.downpayment > lead.future_contract_value or lead.downpayment < 0:
                    addons = lead.addons.filter(lambda a: a.offer_version.offer.type == AddOnType.deposit_change)
                    for addon in addons:
                        addon.delete()
                        flush()
                    AddonService.update_lead_addons(lead)
                ReconciliationService.reconcile_paid_lead_after_editing(lead)
                commit()
            except Exception as e:
                # If it's that error it could not actually be fixed
                # Otherwise we raise
                if str(e) != 'AMOUNT_OVER_BALANCE':
                    raise e

        print(f'Total clients that received a new payment: {total_contracts_new_payment}')

        def max_pending_for_query(l):
            return (l.offer.registration_fee +
                (l.offer.base_price_amount/l.offer.base_price_credit)*(l.offer.time_to_ownership_in_days-l.offer.free_credit_at_start) +
                l.loan_addons_value + l.lump_sum_addons_value - l.already_paid + l.total_blocked)
        
        wrong_maximum_leads = Lead.select(lambda l: l.offer and l.offer_editing_locked and max_pending_for_query(l) < Decimal('-0.005')) # equivalent to round(max_pending_for_query(l), 2) < 0
        wrong_offers = Offer.select(lambda o: o.time_to_ownership_in_days < o.free_credit_at_start or not o.can_be_completed) # filter out broken offers
        wrong_maximum_leads = wrong_maximum_leads.filter(lambda l: l.offer not in wrong_offers)
        print(f'Fixing {wrong_maximum_leads.count()} leads with wrong maximum pending')
        for lead in wrong_maximum_leads:
            print(f'Fixing lead {lead.id}')
            if lead.contract:
                LogAPI.Warning(f'Lead [{lead.id}] has wrong maximum pending of [{lead.maximum_pending}] but has a contract')
                continue
            ReconciliationService.prepare_paid_lead_for_editing(lead)
            if lead.downpayment > lead.future_contract_value or lead.downpayment < 0:
                addons = lead.addons.filter(lambda a: a.offer.type == AddOnType.deposit_change)
                for addon in addons:
                    addon.delete()
                    flush()
                AddonService.update_lead_addons(lead)
            ReconciliationService.reconcile_paid_lead_after_editing(lead)
            commit()

    @classmethod
    @db_session
    def migrate_wallets_strings_phones_to_objects(cls):
        EXTENSION = '+' + SettingsService.get_setting('PhoneExtension')
        EXTENSION_LENGTH = len(EXTENSION)
        MAX_LENGTH = EXTENSION_LENGTH + SettingsService.get_setting('PhoneLength')
        MIN_LENGTH = EXTENSION_LENGTH + SettingsService.get_setting('PhoneLengthMin')

        wallets_to_fix = PaymentWallet.select(lambda w: 
            w.account_phone_number.startswith(EXTENSION) and
            MIN_LENGTH <= len(w.account_phone_number) and
            len(w.account_phone_number) <= MAX_LENGTH and 
            not w.phone_number
        )

        print(f'Fixing {wallets_to_fix.count()} wallets with phone number as string but not as object')
        for wallet in wallets_to_fix:
            AddPhoneNumberService.add_phone_number_to_wallet(wallet.account_phone_number, wallet)

    @classmethod
    @db_session
    def fix_duplicated_operational_permissions(cls):

        users = select(user for user in User if user.roles_in_entities.filter(lambda rie: not rie.entity).count() > 1)
        print(f'Fixing {users.count()} users with duplicated "in all" operational permissions')
        for user in users:
            ops = user.roles_in_entities.filter(lambda rie: not rie.entity)
            for op in ops[:][1:]:
                op.delete()


    @classmethod
    @db_session
    def fix_orphaned_persons(cls):
        orphaned_persons = orm.select(p for p in Person if p.is_orphaned)
        count = orphaned_persons.count()
        if count > 0:
            LogService.Warning(f'Found [{count}] orphaned persons. ')
            person_ids = orm.select(p.id for p in orphaned_persons)[:]
            for person_ids_chunk in cls.chunker(person_ids, 100):
                persons = orm.select(p for p in Person if p.id in person_ids_chunk)
                for person in persons:
                    person.delete()
                orm.commit()
                count = count-100
                print(f'{count} orphaned persons left to delete.')


    @classmethod
    @db_session
    def populate_person_id_sms_db(cls):

        entities = [IncomingSMS, OutgoingSMS]

        for entity in entities:
            print('Migrating {}'.format(entity.__name__))
            with db_session:
                total_count = orm.select(e.id for e in entity).max() or 0
            if total_count == 0:
                continue
            last_updated = total_count+1
            print(f'Total SMS to update: {total_count}')
            while last_updated >= 0:
                with db_session:
                    smss = orm.select(e for e in entity if e.id >= last_updated-10000 and e.id < last_updated and not e.person_id).order_by(orm.desc(1))
                    for sms in smss:
                        obj = sms.to_standard().User
                        if isinstance(obj, Person):
                            sms.person_id = obj.id
                        if isinstance(obj, (User, Client, Lead)):
                            sms.person_id = obj.person.id
                        orm.commit()
                    last_updated -= 10000
                    print(f'SMS remaining: {max(last_updated,0)/total_count*100}%')

    @classmethod
    @db_session
    def fix_duplicated_questions(cls):

        forms = Form.select()
        for form in forms:
            print(f'Sanitizing form {form.name}')
            questions = select(oq.question for v in form.versions for oq in v.questions)
            print(f'Found {questions.count()} questions')
            for question in questions:
                if question._status_ in {'marked_to_delete', 'deleted', 'cancelled'}: #was removed
                    continue
                duplicated_questions = select(q for q in questions if q.name == question.name and q != question)
                if duplicated_questions:
                    print(f'Analysing question {question.name}')
                    print(f'Found {duplicated_questions.count()} duplicated questions for {question.name}')
                renamed = 1
                while select(q for q in questions if q.name == question.name and q != question):
                    dquestion = duplicated_questions.first()
                    if compare_attrs(question, dquestion):
                        assert question != dquestion
                        for oq in dquestion.orderInSurvey:
                            oq.question = question
                        for answer in dquestion.answers:
                            answer.question = question
                        dquestion.delete()
                        print('One question merged')
                    else:
                        renamed += 1
                        dquestion.name = f'{dquestion.name}_{renamed}'
                        print('One question renamed')

            def compare_attrs(q1, q2):
                ATTRS = ['name', 'type', 'version', 'usable', 'icon', 'unit', 'isInt', 'minValue', 'maxValue']
                for attr in ATTRS:
                    if getattr(q1, attr) != getattr(q2, attr):
                        return False
                for t1 in q1.text:
                    if not q2.text.select(lambda t2: t2.language == t1.language and t2.fullQuestion == t1.fullQuestion and t2.variableName == t1.variableName).exists():
                        return False
                for c1 in q1.choices:
                    if not q1.choices.select(lambda c2: c2.order == c1.order and c2.value_numeric == c1.value_numeric).exists():
                        return False
                return True

    @classmethod
    @db_session
    def populate_value_change_events(cls):
        loan_value_addons = ContractAddOn.select(lambda a: a.offer.type == AddOnType.loan and a.loan)
        for addon in loan_value_addons:
            if not addon.contract.contract_events.filter(lambda e: e.type == ContractEventType.value_change and e.time == addon.time_approved):
                ContractEventService.create_contract_value_change(addon.contract, addon.sale_approved_by, addon.time_approved, addon)

    @classmethod
    @db_session
    def fix_phone_numbers(cls):
        bad_contact_phones = Person.select(lambda p: p.contactPhone and (p.contactPhone.person != p or not p.contactPhone.person))
        if bad_contact_phones.count() > 0:
            LogService.Warning(f'Fixing [{bad_contact_phones.count()}] bad phone numbers.')
            for p in bad_contact_phones:
                p.contactPhone.person = p
            print(f'Fixed phone numbers')

    @classmethod
    @db_session
    def remove_empty_repayments(cls):

        repayments = ContractRepayment.select(
            lambda r: r.amount == 0 and not r.discount_type and not r.reconciled_payments and not r.contract_event and not r.converse
        )
        print(f'Removing {repayments.count()} empty repayments')
        contracts_affected = []
        for r in repayments:
            if not r.contract.reference in contracts_affected:
                contracts_affected.append(r.contract.reference)
            r.delete()
        print(f'Empty payments removed, contracts affected: {contracts_affected}')


    @classmethod
    def fix_survey_answer_missing_client(cls):
        page_size = 1000
        with orm.db_session:
            all_answers = SurveyAnswer.select().filter(lambda s: not s.client_answering).order_by(1)
            count = all_answers.count()
        number_of_pages = math.ceil(count / page_size)
        for page_n in range(1, number_of_pages + 1):
            try:
                with orm.db_session:
                    cls._process_page_no_client(all_answers, page_n, number_of_pages, page_size)
            except Exception as e:
                with orm.db_session:
                    cls._process_page_no_client(all_answers, page_n, number_of_pages, page_size)

    @classmethod
    def _process_page_no_client(cls, all_answers, page_n, number_of_pages, page_size):
        # We do the pages in reverse because the list size reduces with the passes
        print(f'Page {page_n} of {number_of_pages} - {(number_of_pages+1)-page_n}')
        answer_page = all_answers.page((number_of_pages+1)-page_n, page_size)
        for ans in answer_page:
            try:
                person = ans.client_answering.person if ans.client_answering else None
                if not person:
                    person = ans.lead_answering.person if ans.lead_answering else ans.personAnswering
                if not person:
                    LogService.Warning(f'Answer [{ans.id}] has no person. ')
                else:
                    if not ans.client_answering and person.client:
                        ans.client_answering = person.client
            except Exception as e:
                LogService.FatalNoRequest(e)
        orm.commit()

    @classmethod
    @db_session
    def create_first_bill(cls):
        if not config.ENABLE_ENTERPRISE_FEATURES:
            return
        from enterprise_features.services.billing_service import BillingService
        SettingsService.set_defaults()
        BillingService.update_billing()
    
    @classmethod
    @db_session
    def fix_client_registered_with_lead_unlocked(cls):
        leads = select(rp.lead for rp in ReconciledPayment if rp.type == ReconciledPaymentType.blocked_during_lead_editing and rp.lead.contract)
        print(f'Found {leads.count()} leads to fix')
        system_user = User.get_system_user()
        for lead in leads:
            for rp in lead.contract.repayments:
                for r in rp.reconciled_payments:
                    r.delete()
                rp.delete()
            lead.offer_editing_locked = True
            ReconciliationService.reconcile_paid_lead_after_editing(lead)
            ContractCreationService._create_and_link_first_repayment(lead.contract, system_user)
            ContractRepaymentService.repay_and_reconcile(lead.contract, force_time=lead.contract.start_time)

    @classmethod
    @db_session
    def fix_manual_payments_in_cash_wallets(cls):
        payments = Payment.select(lambda p: p.back_payment is None and p.PaymentWallet.Type == PaymentWalletType.agent_collection)
        print(f'Found {payments.count()} payments to fix')
        for p in payments:
            LogAPI.Warning(f'Payment with reference [{p.Reference}] has no back payment and is in cash wallet.')
            new_name = p.PaymentWallet.FullName + ' [Fix]'
            new_wallet = PaymentWallet.get(FullName=new_name)
            p.check_coherence_flag = False
            p.PaymentWallet = new_wallet or PaymentWallet(
                RegistrationDate=p.PaymentTime,
                FullName=new_name,
                account_phone_number=p.PaymentWallet.account_phone_number or '',
                phone_number=p.PaymentWallet.phone_number,
                Type=PaymentWalletType.mobile_money,
                operator=p.PaymentWallet.operator or '',
            )

    @classmethod
    @db_session
    def add_fake_id_to_entities(cls):
        for entity in OperationalEntity.select(lambda oe: oe.code == ''):
            entity.code = str(entity.id+ENTITIES_OLD_ID_OFFSET)

    @classmethod
    def migrate_audit_log(cls):
        from shared.model.activity_log_model import (ActivityLogEntry,
                                                     OldActivityLogEntry,
                                                     audit_db)
        with db_session:
            total_count = old_entries = orm.select(e.id for e in OldActivityLogEntry).max()
        pages = int(total_count/10000)+2
        for page in range(1,pages):
            with db_session:
                new_entries = []
                old_entries = orm.select(e for e in OldActivityLogEntry if e.id > (page-1)*10000 and e.id <= page*10000).order_by(1)
                for entry in old_entries:
                    new_entries.append({
                        'time': entry.time,
                        'user': entry.user.id if entry.user else None,
                        'ip': entry.ip,
                        'path': entry.path,
                        'method': entry.method,
                        'args': json.dumps(entry.args),
                        'data': json.dumps(entry.data),
                        'app': entry.app,
                        'user_agent': json.dumps(entry.user_agent)
                    })
                if new_entries:
                    cls._bulk_insert_pg(audit_db, ActivityLogEntry, new_entries)
                    orm.commit()
                    old_entries.delete(bulk=True)
                    orm.commit()
                print(f'Entries processed: {page*10000}/{total_count}')

    @classmethod
    def _bulk_insert_pg(cls, db, table, objects):
        from psycopg2.extras import execute_values
        sql = 'INSERT INTO "'+str(table._table_)+'" ('+",".join(["\""+key+"\"" for key,value in objects[0].items()])+') VALUES %s'
        value_array = [[value for key,value in obj.items()] for obj in objects]
        con = db.get_connection()
        cur = con.cursor()
        execute_values(cur, sql, value_array)

    @classmethod
    @db_session
    def migrate_existing_usernames_to_emails(cls):
        users = orm.select(user for user in User if user.username and not user.email)
        print(f'Migrating {users.count()} users with usernames to email')
        for user in users:
            if '@' in parseaddr(user.username)[1]:
                user.email = user.username

    @classmethod
    def _replace_nan_with_null_and_add_constraint(cls, entities, db):
        for entity in entities:
            float_columns = get_float_columns(entity)
            print(f'Replacing NaN with NULL and adding constraint to {entity.__name__}')
            try:
                for column in float_columns:
                    update_nan_to_null_command = f'UPDATE {entity.__name__} SET {column} = NULL WHERE {column} = double precision \'NaN\';'
                    add_not_nan_constraint = f'ALTER TABLE {entity.__name__} ADD CONSTRAINT {column}_not_nan CHECK ({column} != double precision \'NaN\');'
                    db.execute(update_nan_to_null_command)
                    db.execute(add_not_nan_constraint)
                    orm.commit()
            except Exception as e:
                print(f"Error while replacing NaN with NULL: {str(e)}")

    @classmethod
    @db_session
    def replace_nan_with_null(cls):
        paygops_entities = [Person, OperationalEntity, Metric, StoredFile, Answer, QuestionChoice]
        accounting_db_entities = [Expense]

        cls._replace_nan_with_null_and_add_constraint(paygops_entities, core_db)
        cls._replace_nan_with_null_and_add_constraint(accounting_db_entities, accounting_db)
    
    @classmethod
    @db_session
    def reverse_downpayments_for_cancelled_contracts(cls):
        repayments_with_incorrect_type = ContractRepayment.select(lambda r: r.discount_type == ContractRepaymentDiscountTypes.downpayment and r.converse)
        for repayment in repayments_with_incorrect_type:
            repayment.converse.discount_type = ContractRepaymentDiscountTypes.downpayment_reversal

    @classmethod
    @db_session
    def migrate_existing_contract_addons_to_delivered(cls):
        ContractAddOn.before_update = lambda p: None
        ContractAddOn.after_update = lambda p: None
        def mark_addon_delivered(addon):
            addon.delivered = True
        partial_delivery_addons = select(a.id for a in ContractAddOn if not a.delivered and a.time_approved > datetime(2024,1,25) and a.offer_version.id not in [717, 718, 16, 17])[:]
        addons = select(a for a in ContractAddOn if not a.pending and not a.cancelled and not a.delivered and (a.id not in partial_delivery_addons))
        cls.chunk_executer(addons, ContractAddOn, lambda a: mark_addon_delivered(a), 'addon delivered status migration', chunk_size=1000)
        background_migration_task.delay("update_all_in_model_in_analytical_db", model="AddOns")

    @classmethod
    def update_addon_cached_paid_status(cls):
        """
        Updates the cached_paid property for all addons where the actual paid status
        doesn't match the cached value.
        """
        from payg_loan_system.contracts.models.addons_model import ContractAddOn
        from pony.orm import db_session, select, commit
        
        with db_session:
            # Find addons where paid status doesn't match cached_paid
            mismatched_addons = select(
                addon for addon in ContractAddOn 
                if addon.paid != addon.cached_paid
            )
            
            count = mismatched_addons.count()
            if count == 0:
                print("No addons with mismatched paid status found.")
            
            # Update cached properties for each addon
            for addon in mismatched_addons:
                addon.update_cached_properties()
            
            commit()
            print(f"Updated cached_paid status for {count} addons.")

    @classmethod
    @db_session
    def cleanup_outdated_status_changes_history(cls):
        """
        Clean up StatusChangesHistory entries that have status_id references to non-existent LeadStatus records.
        This will set those status_id fields to None while preserving the status name in the status field.
        """
        from sales_system.leads.models.status_change_history import StatusChangesHistory
        from sales_system.leads.models.lead_status import LeadStatus
        from pony.orm import select

        # Get all StatusChangesHistory entries that have a status_id
        lead_statuses = select(ls.id for ls in LeadStatus)[:]
        history_entries = select(h for h in StatusChangesHistory if h.status_id and h.status_id.id not in lead_statuses)
        print(f'Found {history_entries.count()} history entries to fix')
        
        def clean_entry(entry):
            entry.status_id = None
        
        # Use chunk_executer to process entries in chunks
        cls.chunk_executer(history_entries, StatusChangesHistory, clean_entry, 'cleanup outdated status changes history', chunk_size=5000)
        
        # Log the completion
        print(f"Migration completed at {datetime.now()}")

    @classmethod
    @db_session
    def update_expected_payments_for_long_contracts(cls):
        from payg_loan_system.contracts.services.contract_cache_service import ContractCacheService
        """
        Update the expected payments table for contracts with more than 2*365 installments.
        This is needed because these contracts were previously skipped in the expected payments calculation.
        """
        contracts = Contract.select()
        print(f'Found {contracts.count()} contracts to be processed for expected payments update check')
        
        def update_contract(contract):
            # Force recalculation of expected payments table
            if contract.get_total_number_installments() > 2*365:
                ContractCacheService.update_expected_paid(contract, force=True)
        
        # Use chunk_executer to process contracts in chunks
        cls.chunk_executer(contracts, Contract, update_contract, 'update expected payments for long contracts', chunk_size=100)


@worker_app.task
def background_migration_task(name, *args, version=None, **kwargs):
    try:
        print('Running background migration task: '+name)
        getattr(BackgroundMigrations, name)(*args, **kwargs)
    except Exception as e:
        if version:
            LogAPI.Error(f'Error in background migration {name} - Rolling back version {version}')
            try:
                migration_commands.down(version)
            except Exception as m:
                print(f'Could not rollback version {version} - {m}')
                pass
        LogService.FatalNoRequest(e)
        raise e

