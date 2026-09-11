from datetime import datetime, timedelta
from datetime import datetime
from core_system.operational_entities.services.client_group_getter_service import ClientGroupGetterService
from core_system.person.services.person_getter_service import PersonGetterService
from payg_loan_system.contracts.models.addons_model import ContractAddOn
from pony.orm import select
from payg_loan_system.contracts.models.addon_loan_extension_mode import AddOnLoanExtensionMode
from payg_loan_system.contracts.services.addon_service import AddonService
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService
from payg_loan_system.offers.services.list_offer_service import ListOfferService
from payg_loan_system.offers.services.offer_entity_restriction_service import OfferEntityRestrictionService
from payg_loan_system.payments.services.payment_getter_service import PaymentGetterService
from sales_system.leads.services.lead_edit_permissions_checker import EditLeadPermissionChecker
from sales_system.leads.services.lead_error_messages_service import LeadErrorMessagesService
from core_system.client.services.client_getter_service import ClientGetterService
from messages_system.services.message_service import MessageService
from pony.orm.core import MultipleObjectsFoundError
import json
import random
from decimal import Decimal
from sales_system.leads.models.reasons_for_not_buying import ReasonsForNotBuying
from sales_system.leads.models.status_category import DECISION_MADE_CATEGORIES, StatusCategory
from sales_system.lead_generator.services.lead_generator_getter_service import LeadGeneratorGetterService
from sales_system.leads.services.lead_status_change_service import LeadStatusChangeService
from sales_system.leads.services.lead_status_service import LeadStatusService
from shared.helpers.date_helper import parse_datetime
from shared.logger.loggers import Error
from shared.api_helpers.hook_helpers.process_hook import add_hook_after_commit
from core_system.portfolios.services.portfolio_getter_service import PortfolioGetterService
from core_system.person.services.edit_person_service import EditPersonService
from payg_loan_system.payments.models.payment import Payment
from payg_loan_system.payments.services.reconciliation_service import ReconciliationService
from payg_loan_system.actions.collect_cash import collect_cash
from shared.services.settings_service import SettingsService
from core_system.core_entities import db
from shared.services.base_service import BaseService
from shared.validators.delivery_date import validate_planned_delivery_dates


class EditLeadService(BaseService):

    @classmethod
    def validate_data(cls, lead, data, user):
        if not user.can_access('EditLeads', person=lead.person, check_special=True):
            raise Error('INSUFFICIENT_PERMISSION', permission='EditLeads')
        data = CheckedData(lead, data, user)
        EditPersonService.validate_data(data)

    @classmethod
    def _edit_from_data_and_user(cls, this_lead, data, user):
        return cls.edit_lead(this_lead, data, user)

    @staticmethod
    def clean_nones(v):
        return [i for i in v if i] if isinstance(v, list) else v

    @classmethod
    def _check_edit_restricted_details_permission(cls, data, name, old_value):
        if name in data and cls.clean_nones(data[name]) != old_value:
            raise Error('INSUFFICIENT_PERMISSION', permission='EditRestrictedPersonalDetailsLeads')

    @classmethod
    def edit_lead(cls, this_lead, data, user):
        if not user.can_access('EditLeads', person=this_lead.person, check_special=True):
            raise Error('INSUFFICIENT_PERMISSION', permission='EditLeads')
        data = CheckedData(this_lead, data, user)
        lead_in_restricted_state = LeadStatusService.lead_is_in_restricted_status(this_lead)
        if lead_in_restricted_state and not user.can_access('EditRestrictedPersonalDetailsLeads', person=this_lead.person):
            existing_numbers = [p.number for p in this_lead.person.phoneNumbers]
            preferred_phone_number = this_lead.person.contactPhone.number if this_lead.person.contactPhone else None
            cls._check_edit_restricted_details_permission(data, 'name', this_lead.person.name)
            cls._check_edit_restricted_details_permission(data, 'surname', this_lead.person.surname)
            cls._check_edit_restricted_details_permission(data, 'custom_id', this_lead.person.custom_id)
            cls._check_edit_restricted_details_permission(data, 'preferred_phone_number', preferred_phone_number)
            cls._check_edit_restricted_details_permission(data, 'number', preferred_phone_number)
            cls._check_edit_restricted_details_permission(data, 'phone_numbers', existing_numbers)
            cls._check_edit_restricted_details_permission(data, 'phone_numbers', existing_numbers)

        if "preferred_phone_number" in data:
            preferred_phone_number = this_lead.person.contactPhone.number if this_lead.person.contactPhone else None
            if lead_in_restricted_state and not user.can_access('EditRestrictedPersonalDetailsLeads', person=this_lead.person):
                cls._check_edit_restricted_details_permission(data, 'preferred_phone_number', preferred_phone_number)
            elif not user.can_access('DeletePhoneNumbers', person=this_lead.person):
                cls._check_edit_restricted_details_permission(data, 'preferred_phone_number', preferred_phone_number)

        this_lead.modifiedDate = datetime.now()

        lead_generator = LeadGeneratorGetterService.get_from_user_and_id(user, data.get('generator')) if data.get('generator') else None
        if lead_generator:
            this_lead.generator = lead_generator
        
        if 'allocated_device' in data:
            if not data['allocated_device']:
                if this_lead.allocated_device:
                    if not user.can_access('EditAllocatedDeviceLeads', person=this_lead.person):
                        raise Error('INSUFFICIENT_PERMISSION', permission='EditAllocatedDeviceLeads')
                    this_lead.allocated_device = None
            else:
                allocated_device = DeviceGetterService.get_from_user_and_properties(user, composed_serial=data["allocated_device"], strict=True)
                if allocated_device != this_lead.allocated_device:
                    if not user.can_access('EditAllocatedDeviceLeads', person=this_lead.person):
                        raise Error('INSUFFICIENT_PERMISSION', permission='EditAllocatedDeviceLeads')
                    if allocated_device.allocated_lead:
                        raise Error('DEVICE_ALREADY_ALLOCATED', lead_id=allocated_device.allocated_lead.id)
                    if allocated_device.contract:
                        raise Error('DEVICE_ALREADY_REGISTERED', device_owner_id=allocated_device.contract.client.id)
                    this_lead.allocated_device = allocated_device

        generation_date = data.get('generation_date')
        if generation_date:
            this_lead.receptionTime = parse_datetime(generation_date)

        lead_client = this_lead.person.client
        client_mobile_uuid = data.get('client_mobile')
        if client_mobile_uuid:
            if lead_client and lead_client.mobile_uuid != client_mobile_uuid:
                client = ClientGetterService.get_list(user, for_new_contract=True).filter(lambda c: c.mobile_uuid == client_mobile_uuid).get()
                if not client:
                    raise Error('Client not found')
                cls._edit_lead_person(this_lead, client.person)
        client_id = data.get('client')
        if client_id:
            if lead_client and lead_client.id != client_id:
                client = ClientGetterService.get_list(user, for_new_contract=True).filter(lambda c: c.id == client_id).get()
                if not client:
                    raise Error('Client not found')
                cls._edit_lead_person(this_lead, client.person)
        EditPersonService.edit_person_from_data(this_lead.person, data, edit_phone_numbers=True, user=user)

        if 'next_contact' in data:
            if cls.validate_required_fields('next_planned_contact',data.get('next_contact')):
                this_lead.nextContact = parse_datetime(data.get('next_contact'))
            else:
                this_lead.nextContact = None

        if 'reasons_for_not_buying' in data:
            cls.add_reasons_to_lead(this_lead, data.get('reasons_for_not_buying'))

        commission = data.get('commission')
        if commission:
            try:
                commission_int = int(commission)
                this_lead.commission = commission_int
            except Exception as error:
                raise Error('INVALID_COMMISSION_VALUE')

        commission_note = data.get('commission_note', '')
        if 'commission_note' in data:
            this_lead.commissionComment = commission_note if commission_note else ''

        status = data.get('status')
        status = LeadStatusService.get_status(status)
        if status and status != this_lead.status:
            status_comment = cls.validate_required_fields('comment_on_status', data.get('status_comment', ''))
            LeadStatusChangeService.update(this_lead) #We ensure status is updated beforehand
            if status not in LeadStatusChangeService.get_allowed_statuses_from_lead(this_lead, user):
                if status.category in DECISION_MADE_CATEGORIES and this_lead.awaiting_decision:
                    LeadStatusChangeService.approve_lead(this_lead, status_comment, user)
                else:
                    raise Error('STATUS_NOT_ALLOWED', status.name, this_lead.status.name)
            LeadStatusChangeService.set_status(this_lead, status, status_comment, user)
        elif 'comment_on_status' in data or 'status_comment' in data:
            status_comment = cls.validate_required_fields('comment_on_status', data.get('status_comment', ''))
            if status_comment and status_comment != this_lead.status_comment:
                LeadStatusChangeService.set_status(this_lead, this_lead.status, status_comment, user)

        if 'portfolio_id' in data or 'portfolio' in data:
            portfolio = None
            portfolio_id = data.get('portfolio_id', data.get('portfolio'))
            this_lead_portfolio_id = this_lead.portfolio.id if this_lead.portfolio else ''
            if this_lead_portfolio_id or portfolio_id and portfolio_id != this_lead_portfolio_id:
                user.check_access('EditPortfolioLeads', person=this_lead.person, check_special=True)
                if portfolio_id:
                    portfolio = PortfolioGetterService.get_from_user_and_id(user, portfolio_id, strict=True)
            else:
                portfolio = this_lead.portfolio
            this_lead.portfolio = cls.validate_required_fields('portfolio', portfolio)

        client_group_id = data.get('client_group_id', data.get('client_group'))
        
        if 'client_group_id' in data:
            client_group_id = cls.validate_required_fields('client_group', data.get('client_group_id', data.get('client_group')))
            if client_group_id:
                current_id = this_lead.person.client_group.id if this_lead.person.client_group else None
                if client_group_id != current_id:
                    client_group = ClientGroupGetterService.get_from_user_and_id(user, client_group_id, strict=True)
                    this_lead.person.client_group = client_group
            else:
                this_lead.person.client_group = None


        if 'offer_editing_locked' in data and bool(data.get('offer_editing_locked')) != this_lead.offer_editing_locked:
            this_lead.offer_editing_locked = bool(data.get('offer_editing_locked'))
            cls._apply_offer_lock(this_lead, user)

        offer = data.get('offer_id', data.get('offer'))
        if offer:
            this_offer = ListOfferService.get_from_user_and_id(user, offer, strict=True)
            if this_offer != this_lead.offer:
                if this_lead.loan_addons.count() and not this_offer.allow_loan_addons:
                    raise Error('LEAD_HAS_LOAN_ADDONS')
                if this_lead.loan_addons.filter(lambda a: a.loan_mode in AddOnLoanExtensionMode.duration).count() and this_lead.addons_price + this_offer.base_price_amount == 0:
                    raise Error('LEAD_OFFER_NOR_VALID_WITH_DURATION_ADDONS')
                EditLeadPermissionChecker.check_permissions(this_lead, user)
                cls._set_lead_offer(this_lead, this_offer, user)
        elif 'offer_id' in data or 'offer' in data:
            if this_lead.addons.count() > 0:
                raise Error('CANNOT_REMOVE_OFFER_IF_ADDONS')
            EditLeadPermissionChecker.check_permissions(this_lead, user)
            cls._set_lead_offer(this_lead, None, user)
        
        if this_lead.allocated_device and this_lead.offer and not this_lead.allocated_device.can_use_offer(this_lead.offer):
            raise Error('Device not allowed for this offer')
        
        # Special Add-On handling for internal use for now
        removed_addons_data = data.get('remove_add_ons')
        if removed_addons_data:
            for addon_id in removed_addons_data:
                this_addon = ContractAddOn.get(id=addon_id)
                AddonService.cancel(this_addon, user)

        addons_data = data.get('add_ons')
        if addons_data:
            if not this_lead.offer:
                raise Error('CANNOT_REMOVE_OFFER_IF_ADDONS')
            for addon_data in addons_data:
                addon_data['lead_id'] = this_lead.id
                if addon_data.get('id'):
                    this_addon = ContractAddOn.get(id=addon_data.get('id'))
                    AddonService.edit_from_data_and_user(this_addon, addon_data, user)
                else:
                    AddonService.add_from_data_and_user(addon_data, user)

        payment_reference = data.get('payment_reference')
        if payment_reference:
            if payment_reference == 'REFUND_DEPOSIT':
                cls.refund_deposit(this_lead)
            elif payment_reference == 'CASH_COLLECTED':
                amount = data.get('amount')
                cls.pay_deposit_in_cash(this_lead=this_lead, acting_user=user, amount=amount)
            else:
                try:
                    payment = PaymentGetterService.get_from_user_and_properties(user, Reference=payment_reference, strict=True)
                except MultipleObjectsFoundError:
                    raise Error('MULTIPLE_PAYMENT_FOUND')
                answer = ReconciliationService.get_answer_for_lead(this_lead, payment, user=user)
                MessageService.send_answer_to_person(answer, this_lead.person)

        if data.get('promised_to_pay_date'):
            this_lead.promisedToPay = parse_datetime(data.get('promised_to_pay_date'))
        elif 'promised_to_pay_date' in data:
            this_lead.promisedToPay = None

        agreed_delivery_date = parse_datetime(data.get('planned_delivery_date'))
        if agreed_delivery_date:
            validate_planned_delivery_dates(agreed_delivery_date, user)
            this_lead.agreedDeliveryDate = agreed_delivery_date
            if this_lead.loan_addons.count():
                # If the lead has addons which don't have an explicit delivery date, we trigger the planned delivery date webhook
                for addon in this_lead.addons:
                    if not addon.planned_delivery_date:
                        AddonService.send_data_to_hook_delivery_date_change(addon, user, None, agreed_delivery_date)
        elif 'planned_delivery_date' in data and this_lead.agreedDeliveryDate:
            for addon in this_lead.addons:
                if not addon.planned_delivery_date:
                    AddonService.send_data_to_hook_delivery_date_change(addon, user, this_lead.agreedDeliveryDate, None)
            this_lead.agreedDeliveryDate = None

        if 'addons_planned_delivery_date' in data and user.can_access('EditPlannedDeliveryDateAddOns', person=this_lead.person):
            schedule = False
            if data.get('schedule_individual_addon_delivery_dates', False):
                schedule = True
            for key, val in data['addons_planned_delivery_date'].items():
                addon = ContractAddOn.get(reference=key)
                if not addon:
                    raise Error('Addon reference not found')
                if val in ['None', None, 'null', ''] or not schedule:
                    AddonService.send_data_to_hook_delivery_date_change(addon, user, addon.planned_delivery_date, None)
                    addon.planned_delivery_date = None
                else:
                    date = parse_datetime(val)
                    validate_planned_delivery_dates(date, user)
                    AddonService.send_data_to_hook_delivery_date_change(addon, user, addon.planned_delivery_date, date)
                    addon.planned_delivery_date = val


        EditPersonService.edit_phone_numbers(this_lead.person, data, user)

        LeadStatusChangeService.update(this_lead)

        if data.get('custom_data'):
            cls._process_custom_data_update(this_lead, data)

        if data.get('skip_hook', False) not in [True, 'true']:
            add_hook_after_commit(db, 'lead_edited', this_lead.get_serialized_object())
        return this_lead

    @classmethod
    def add_reasons_to_lead(cls, this_lead, reasons):
        this_lead.reasons_for_not_buying.clear()
        if reasons:
            for reason in reasons:
                this_reason = cls._get_reason_object(reason)
                this_lead.reasons_for_not_buying.add(this_reason)

    @classmethod
    def get_human_readable_message(cls, error, user=None):
        return LeadErrorMessagesService.get_human_readable_error(error, user=user)

    @classmethod
    def _apply_offer_lock(cls, lead, user):
        if lead.offer_editing_locked:
            ReconciliationService.reconcile_paid_lead_after_editing(lead)
            if LeadStatusChangeService.lead_is_complete(lead):
                LeadStatusChangeService.remove_lead_approval(lead, user, 'Automatically unapproved after offer editing')
            else:
                LeadStatusChangeService.remove_lead_approval(lead, user, set_status=False)
                LeadStatusChangeService.update(lead)
        else:
            print('offer unlock')
            EditLeadPermissionChecker.check_permissions(lead, user)
            ReconciliationService.prepare_paid_lead_for_editing(lead)

    @classmethod
    def _get_reason_object(cls, reason):
        try:
            reason_id = int(reason)
            this_reason = ReasonsForNotBuying.get(id=reason_id)
            if not this_reason:
                raise Error('INVALID_REASON_FOR_NOT_BUYING_ID')
        except ValueError:
            this_reason = ReasonsForNotBuying.get(name=reason)
            if not this_reason:
                raise Error('INVALID_REASON_FOR_NOT_BUYING')
        return this_reason

    @classmethod
    def _set_lead_offer(cls, this_lead, this_offer, user):
        if this_offer != this_lead.offer:
            if this_offer is not None:
                OfferEntityRestrictionService.assert_offer_allowed_for_lead(
                    this_offer, this_lead.person.village
                )
            this_lead.offer = this_offer
            this_lead.offer_editing_locked = True
            cls._apply_offer_lock(this_lead, user)
            LeadStatusChangeService.offer_change_update(this_lead, user)
            AddonService.update_lead_addons(this_lead)

    @classmethod
    def _generate_install_uuid(cls):
        return (''.join(random.choice('0123456789abcdefghiklmprtuwxy') for i in range(3)) + '' + ''.join(
            random.choice('0123456789abcdefghiklmprtuwxy') for i in range(3))).upper()

    @classmethod
    def pay_deposit_in_cash(cls, this_lead, acting_user, amount=None, offline=False, note=''):
        if not this_lead.offer:
            return [dict({'success': False, 'status': 'LEAD_HAS_NO_OFFER'}, **{'error': 'LEAD_HAS_NO_OFFER'})]
        if offline and this_lead.already_paid:
            cls.refund_deposit(this_lead)
        amount = Decimal(amount) if amount else this_lead.downpayment
        try:
            answer, payment = collect_cash(acting_user, lead=this_lead, amount=amount, note=note)
        except Error as error:
            return [dict({'success': False, 'status': str(error)}, **error.data)]
        answer += ReconciliationService.get_answer_for_lead(this_lead, payment)
        MessageService.send_answer_to_person(answer, this_lead.person)
        return answer

    @classmethod
    def refund_deposit(cls, this_lead):
        if this_lead.contract:
            raise Error('CANNOT_REFUND_INSTALLED_LEAD')
        if not this_lead.reconciled_payments:
            raise Error('PAYMENT_WAS_DELETED')
        if not this_lead.offer_editing_locked:
            raise Error('DEPOSIT_CANNOT_BE_REFUNDED')
        payments = select(r.linked_payment for r in this_lead.reconciled_payments)[:]
        # list conversion needed to force query before deleting                   ^^^
        for reccon_pay in this_lead.reconciled_payments:
            reccon_pay.delete()
        for payment in payments:
            payment.payment_or_reconciled_changed()
        LeadStatusChangeService.update(this_lead)

    @classmethod
    def _process_custom_data_update(cls, this_lead, data):
        updated_custom_data = data.get('custom_data')
        if type(updated_custom_data) is not dict:
            raise Error('INVALID_CUSTOM_DATA_FORMAT')
        for key, value in updated_custom_data.items():
            if not key.startswith('app_'):
                raise Error('INVALID_CUSTOM_DATA_KEY')
            if type(value) is not dict:
                raise Error('INVALID_CUSTOM_DATA_VALUE')
            if len(json.dumps(value)) > 8192:
                raise Error('CUSTOM_DATA_OVERSIZE')
            if not this_lead.custom_data:
                this_lead.custom_data = {}
            this_lead.custom_data[key] = value

    @classmethod
    def _edit_lead_person(cls, this_lead, new_person):
        this_lead.person = new_person
        for rp in this_lead.reconciled_payments:
            rp.cached_person = new_person

    @classmethod
    def validate_required_fields(cls, field_name, value):
        personal_info_settings_obj = SettingsService.get_setting('LeadInfoSettings')
        if personal_info_settings_obj[field_name]['required'] and not value:
            raise Error(f"{field_name} is a required field")
        return value

class CheckedData():

    allowed = ['generation_date', 'generator', 'commission', 'commission_note', 'custom_data', 'portfolio']
    allowed_for_unlocked = ['offer', 'offer_id', 'offer_editing_locked', 'skip_hook', 'add_ons', 'remove_add_ons']
    installed = False
    cancelled = False
    locked = True
    data = {}

    def __init__(self, lead, data, user):

        self.installed = lead.installed
        self.cancelled = lead.cancelled
        self.locked = bool(data.get('offer_editing_locked')) if 'offer_editing_locked' in data else lead.offer_editing_locked
        if not user.can_access('EditInstalledLeads', person=lead.person):
            if self.installed: raise Error('CANNOT_EDIT_INSTALLED_LEAD')
            if self.cancelled: raise Error('CANNOT_EDIT_CANCELLED_LEAD')

        self.data = data

    def __contains__(self, item):
        return item in self.data
    
    def __repr__(self) -> str:
        return str(self.data)
    
    def __getitem__(self, key):
        return self.get(key)

    def get(self, key, *args, **kwargs):
        if key in self.data and not key in self.allowed:
            if self.installed: raise Error('CANNOT_EDIT_INSTALLED_LEAD')
            if self.cancelled: raise Error('CANNOT_EDIT_CANCELLED_LEAD')
        if key in self.data and not key in self.allowed_for_unlocked and not self.locked:
            raise Error('You cannot edit a lead while offer editing is unlocked, please lock and save before editing', code="CANNOT_EDIT_LOCKED_LEAD")
        return self.data.get(key, *args, **kwargs)
