from datetime import datetime, timedelta
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from core_system.users.services.user_getter_service import UserGetterService
from payg_loan_system.contracts.services.addons.addon_offer_getter_service import AddonOfferGetterService
from payg_loan_system.contracts.services.addons.addon_offer_version_getter_service import AddonOfferVersionGetterService
from payg_loan_system.contracts.services.contract_event_service import ContractEventService
from messages_system.services.message_service import MessageService
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService
from payg_loan_system.offers.models import OfferType
from sales_system.leads.services.lead_edit_permissions_checker import EditLeadPermissionChecker
from sales_system.leads.services.lead_getter_service import LeadGetterService
from decimal import Decimal, DecimalException
from payg_loan_system.contracts.services.contract_repayment_service import ContractRepaymentService
from shared.helpers.date_helper import parse_datetime
from shared.helpers.compare_dicts import all_keys_are_in_list

from sales_system.leads.models.status_category import StatusCategory, DECISION_MADE_CATEGORIES
from sales_system.leads.services.lead_status_change_service import LeadStatusChangeService

from pony.orm.core import select, flush
from payg_loan_system.payments.services.reconciliation_service import ReconciliationService
from shared.api_helpers.hook_helpers.process_hook import add_hook_after_commit
from shared.logger.loggers import Error
from payg_loan_system.contracts.models.addons_model import AddOnLoanExtensionMode, ContractAddOn, AddOnType
from payg_loan_system.actions.collect_cash import collect_cash
from payg_loan_system.contracts.services.reconciled_payment_service import ReconciledPaymentService
from payg_loan_system.contracts.services.contract_getter_service import ContractGetterService
from payg_loan_system.contracts.models.contract_status import ContractStatus
from shared.helpers.numbers import round_if_exists
from core_system.core_entities import db
from shared.api_helpers.hook_helpers import process_hook
from shared.services.base_service import BaseService
from shared.services.settings_service import SettingsService
from shared.validators.delivery_date import validate_planned_delivery_dates
from stock_management_system.quantity_stock_models import (
    QuantityStockLocation, QuantityStockMovement)
from stock_management_system.services.product_sub_type_service import ProductSubTypeService
from stock_management_system.services.quantity_stock_movement_service import QuantityStockMovementService
from stock_management_system.services.stock_movement_creation_service import StockMovementCreationService
from stock_management_system.stock_status import StockMovementStatus, StockStatus



class AddonService(BaseService):

    @classmethod
    def get_affected_entity(cls, data, user, **kwargs):
        reference = data.get('contract_reference')
        contract = ContractGetterService.get_from_user_and_properties(user, reference=reference)
        lead_id = data.get('lead_id', data.get('lead'))
        lead = LeadGetterService.get_from_user_and_id(user, lead_id)
        if not contract and not lead:
            raise Error('Neither contract or lead found')
        return (lead or contract).person.village

    @classmethod
    def create(cls, contract, offer_version, quantity_sold, sale_made_by, mobile_uuid=None, loan_mode='', lead=None, note='', reference=None, duplicating=False, cancelled_addon=None, device_serial=None, delivered=None, planned_delivery_date=None, skip_hook=None):
        if not lead and not contract:
            raise Error('To sell an add-on you need to provide either a Lead or a Contract')
        if lead and contract:
            raise Error('You cannot provide both a Lead and a Contract')
        if lead and not lead.offer:
            raise Error('You cannot add an add-on on a lead without an offer')
        if cancelled_addon and cancelled_addon.cancelled_by_addon:
            raise Error('Add-on {reference} already cancelled', reference=cancelled_addon.reference)

        relevant_person = (lead or contract.client).person
        if not sale_made_by.can_access('AddAddOns', person=relevant_person, check_special=True):
            raise Error('INSUFFICIENT_PERMISSION', permission='AddAddOns')

        if not offer_version:
            raise Error('AddonOfferVersion not found')

        if offer_version.offer.is_contract_terms_changes and not sale_made_by.can_access('AddContractTermsChangeAddOns', person=relevant_person):
            raise Error('INSUFFICIENT_PERMISSION', permission='AddContractTermsChangeAddOns')
        device = None
        if offer_version.offer.linked_to_product and not cancelled_addon and offer_version.offer.is_serialized and device_serial:

            device = DeviceGetterService.get_device_from_serial_number_only(device_serial, raise_if_absent=True)
            cls._validate_device_type_compatibility(device, offer_version)

        
        try:
            if device:
                quantity_sold = 1
            elif quantity_sold is not None:
                quantity_sold = Decimal(str(quantity_sold)).normalize()
            else:
                quantity_sold = 1
        except (ValueError, TypeError, DecimalException):
            raise Error('The quantity_sold must be a valid decimal number.')
        if offer_version.offer.allow_decimal_quantities and device and round(quantity_sold, 2) != quantity_sold:
            raise Error('The quantity_sold must have only two decimal digits.')
        if not offer_version.offer.allow_decimal_quantities and device and not float(quantity_sold).is_integer():
            raise Error('The quantity_sold must be a whole number')
        if round(quantity_sold, 2) == 0 and device:
            raise Error('The quantity sold must not be zero.')
        total_amount = round(quantity_sold*offer_version.price, 2)

        if contract and contract.status in [ContractStatus.defaulted, ContractStatus.cancelled]:
            raise Error('The contract is not eligible to be sold an add-on since it is defaulted or cancelled')
        if lead:
            EditLeadPermissionChecker.check_permissions(lead, sale_made_by)

        if not cancelled_addon:
            # We should not check if offer is available as we create a negative addon of the existing one
            cls.check_addon_offer_available(offer_version, contract, lead, duplicating)

        contract_offer = (contract or lead).offer
        if not contract_offer or not contract_offer.allow_loan_addons and offer_version.offer.type == AddOnType.loan:
            raise Error('The contract\'s offer cannot accept loan extensions. Make sure it is a loan offer with add-ons enabled. ')

        if offer_version.offer.type == AddOnType.lump_sum and device and total_amount < 0 and not offer_version.offer.purchasing_addon:
            raise Error('Negative value add-ons cannot be paid as lump-sum add-ons.')

        if loan_mode and offer_version.offer.type not in [AddOnType.loan, AddOnType.deposit_change]:
            raise Error('Loan extension option are only available for Loan addons and Deposit Change addons.')

        if offer_version.offer.type == AddOnType.loan:
            if lead and lead.offer.maximum_value_extension and offer_version.enforce_extension_limit and lead.loan_addons_value + total_amount > lead.offer.maximum_value_extension:
                raise Error(f'Add-on cannot be created. The lead has reached the maximum add-on extension.')
            if contract and contract.offer.maximum_value_extension and offer_version.enforce_extension_limit and contract.offer.maximum_value_extension < contract.get_total_extended() + total_amount:
                raise Error(f'Add-on cannot be created. The contract has reached the maximum extension.')
            
            empty_loan_contract = contract and contract.status == ContractStatus.completed and contract.offer.base_price_amount_can_be_negative
            if not loan_mode and getattr(contract, "status", '') == ContractStatus.completed:
                if empty_loan_contract:
                    loan_mode = AddOnLoanExtensionMode.amount
                else:
                    loan_mode = AddOnLoanExtensionMode.duration
            
        if offer_version.offer.type in [AddOnType.loan, AddOnType.deposit_change] and not loan_mode:
            if not offer_version.offer.loan_mode:
                raise Error('Loan extension option is required')
            loan_mode = offer_version.offer.loan_mode

        if contract and contract.status == ContractStatus.completed and loan_mode == AddOnLoanExtensionMode.amount and not contract.reference_price == 0:
            raise Error('The contract is already completed and cannot be extended by reference pricing change.')
        
        if lead and offer_version.offer.type == AddOnType.loan_duration_change:
            if lead.addons.filter(lambda a: a.offer_version.offer.type == AddOnType.loan_duration_change):
                raise Error('Leads can only have one single add-on of type '+AddOnType.loan_duration_change)
        if contract and offer_version.offer.type == AddOnType.deposit_change:
            raise Error('Deposit change add-ons cannot be added to an on going contract')
        if contract and offer_version.offer.type == AddOnType.loan_duration_change:
            if contract.add_ons.filter(lambda a: a.offer_version.offer.type == AddOnType.loan_duration_change and a.pending):
                raise Error('Contracts can only have one single pending add-on of type '+AddOnType.loan_duration_change)
        if planned_delivery_date and not duplicating:
            validate_planned_delivery_dates(planned_delivery_date, sale_made_by)

        if not reference:
            reference = cls._get_new_reference_for_contract(contract, lead)

        discounted_amount = 0
        if (
            offer_version.offer.type == AddOnType.lump_sum
            and offer_version.offer.purchasing_addon
            and (
                (contract and contract.offer.type != OfferType.lump_sum)
                or lead
            )
        ):
            discounted_amount = total_amount
        if (
            not device
            and offer_version.offer.linked_to_product
            and offer_version.offer.is_serialized
            and quantity_sold > 0
        ):
            total_amount = offer_version.price

        addon = ContractAddOn(
            contract=contract,
            lead=lead,
            offer_version=offer_version,
            quantity_sold=quantity_sold,
            sale_made_by=sale_made_by,
            reference=reference,
            total_amount=total_amount,
            discounted_amount=discounted_amount,
            time_created=datetime.now(),
            loan_mode=loan_mode or '',
            note=note,
            cached_person=contract.client.person if contract else lead.person,
            cancelled_addon=cancelled_addon,
            device=device,
            delivered=delivered or False,
            planned_delivery_date=planned_delivery_date
        )
        cls.consistency_checks(addon)
        if lead:
            cls.update_lead_addons(lead)
        if delivered is not None:
            delivered = delivered in [True, 'true', 'yes', '1']
            cls.set_delivery_status(addon, sale_made_by, delivered)

        if mobile_uuid:
            if ContractAddOn.get(mobile_uuid=mobile_uuid):
                raise Error('Addon already exists')
            addon.mobile_uuid = mobile_uuid
        if not offer_version.offer.need_approval and contract or cancelled_addon:
            delivered = True
            if not device and addon.offer_version.offer.linked_to_product and addon.offer_version.offer.is_serialized:
                delivered = False
            cls.approve(addon, sale_made_by, auto_deliver=delivered)
        elif lead:
            # only update lead status when offer editing is locked
            if lead.offer_editing_locked:
                if (lead.status.category in DECISION_MADE_CATEGORIES or lead.decision) and addon.offer_version.offer.need_approval and not duplicating:
                    LeadStatusChangeService.remove_lead_approval(lead, sale_made_by, 'Automatically Unapproved after new add-on sale')
                LeadStatusChangeService.update(lead, autoreconcile_from_client=not duplicating)
        if skip_hook not in [True, 'true']:
            add_hook_after_commit(db, 'new_addon', addon.get_serialized_object())
            if planned_delivery_date:
                cls.send_data_to_hook_delivery_date_change(addon, sale_made_by, None, planned_delivery_date)

        return addon

    @classmethod
    def lead_consistency_checks(cls, lead):
        if lead.loan_addons.filter(lambda a: a.loan_mode in AddOnLoanExtensionMode.duration).count() and lead.reference_price == 0:
            raise Error('The new contract offer and add-ons configuration is not possible since the reference price would be 0 and there are duration add-ons.')

        if lead.offer and lead.offer.type == OfferType.loan and (lead.future_contract_duration-lead.offer.free_credit_at_start) <= 0:
            raise Error('You cannot reduce the duration of the loan more than the original duration')

        if lead.offer and lead.offer.type == OfferType.loan and lead.downpayment < 0:
            raise Error('You cannot reduce the downpayment below 0')

    @classmethod
    def consistency_checks(cls, addon):
        if addon.contract and addon.offer_version.offer.type != AddOnType.lump_sum and (addon.contract.reference_price+addon.calculate_current_repayment_increase()) <= 0 and not addon.offer_version.offer.purchasing_addon:
            if not (addon.contract.reference_price+addon.calculate_current_repayment_increase() == 0 and addon.contract.offer.base_price_amount_can_be_negative):
                raise Error('The add-on cannot be created. The resulting repayment amount of the contract would be negative or null.')

        if addon.contract and addon.offer_version.offer.type != AddOnType.lump_sum and (addon.contract.get_outstanding_balance() + addon.total_amount)  < 0 and not addon.offer_version.offer.purchasing_addon:
            raise Error('Contract cannot be extended negatively below the amount already paid')

    @classmethod
    def _add_from_data_and_user(cls, data, user):
        sale_made_by = user
        reference = data.get('contract_reference')
        contract = ContractGetterService.get_from_user_and_properties(sale_made_by, reference=reference, strict=True) if reference else None
        lead_id = data.get('lead_id', data.get('lead'))
        lead = LeadGetterService.get_from_user_and_id(user, lead_id, strict=True) if lead_id else None
        offer = AddonOfferVersionGetterService.get_from_user_and_id(user, data.get('offer_version_id', data.get('offer')))
        if not offer and data.get('offer_id'):
            offer = AddonOfferGetterService.get_from_user_and_properties(user, id=data.get('offer_id'))
            if offer and not offer.version_for_sales:
                raise Error(f'Addon offer is not available for sales.', code="ADDON_OFFER_NOT_AVAILABLE")
            offer = offer.version_for_sales
        if not offer and data.get('offer_code'):
            offer = AddonOfferGetterService.get_from_user_and_properties(user, code=data.get('offer_code'))
            if offer and not offer.version_for_sales:
                raise Error(f'Addon offer is not available for sales.', code="ADDON_OFFER_NOT_AVAILABLE")
            offer = offer.version_for_sales
        if not offer:
            raise Error(f'Addon offer not found.', code="ADDON_OFFER_NOT_FOUND")
        
        if offer.offer.purchasing_addon and not user.can_access('AddPurchasingAddOns', person=user.person):
            raise Error('Not enough permissions to create addon')
        
        quantity_sold = data.get('quantity_sold')
        loan_mode = data.get('loan_mode', '')
        note = data.get('note', '')
        if note is not None and not isinstance(note, str):
            note = str(note)
        mobile_uuid = data.get('mobile_uuid')
        device_serial = data.get('device_serial')
        delivered = data.get('delivered')
        planned_delivery_date = parse_datetime(data.get('planned_delivery_date'))
        skip_hook = data.get('skip_hook')
        addon = cls.create(contract, offer, quantity_sold, sale_made_by, loan_mode=loan_mode, lead=lead, note=note, mobile_uuid=mobile_uuid, device_serial=device_serial, delivered=delivered, planned_delivery_date=planned_delivery_date, skip_hook=skip_hook)
        if not addon.sale_approved_by and data.get('approved', False):
            if not user.can_access('ApproveAddOns', person=user.person):
                raise Error('Not enough permissions to approve addons')
            cls.approve(addon, user, auto_deliver=delivered is None)
        if 'cash_collection_agent' in data:
            agent = UserGetterService.get_from_user_and_id(user, data['cash_collection_agent'], strict=True)
            cls.pay_with_cash(addon, agent)
        addon.update_cached_properties() # This is needed to update the paid status properly
        return addon

    @classmethod
    def _edit_from_data_and_user(cls, addon, data, user):
        skip_hook = data.get('skip_hook', False) in [True, 'true']
        if 'cash_collection_agent' in data:
            agent = UserGetterService.get_from_user_and_id(user, data['cash_collection_agent'], strict=True)
            return cls.pay_with_cash(addon, agent)
        person = (addon.lead or addon.contract.client).person
        contract_offer = (addon.contract or addon.lead).offer
        if addon.lead and not addon.contract and not all_keys_are_in_list(data, ['skip_hook', 'planned_delivery_date', 'note']):
            EditLeadPermissionChecker.check_permissions(addon.lead, user)
        delivered = None
        if 'delivered' in data:
            delivered = data['delivered'] in [True, 'true', 'yes', '1']
            cls.set_delivery_status(addon, user, delivered=delivered, skip_hook=skip_hook)
        if 'approved_by' in data and not data.get('approved_by'):
            raise Error('approved_by is required')
        if data.get('approved', False) or data.get('approved_by'):
            if not user.can_access('ApproveAddOns', person=person):
                raise Error('Not enough permissions to approve addons')
            return cls.approve(addon, user, auto_deliver=delivered in [None, True], skip_hook=skip_hook)
        if 'cancelled' in data and data['cancelled']:
            return cls.cancel(addon, user, time_canceled=data.get('time_canceled', None))
        offer_version_id = data.get('offer_version_id', data.get('offer', data.get('offer_id')))
        offer_code =  data.get('offer_code')
        has_offer_changed = offer_version_id or offer_code or data.get('quantity_sold') or data.get('loan_mode')
        if has_offer_changed and addon.contract and not (addon.pending and addon.already_paid == 0):
            raise Error('You cannot change the offer or quantity of an approved or paid addon.')
        elif has_offer_changed and not addon.contract and not addon.lead.can_edit_offer:
            raise Error('You cannot change the offer or quantity when the lead offer is locked.')
        elif has_offer_changed and addon.contract and addon.contract.status in [ContractStatus.defaulted, ContractStatus.cancelled]:
            raise Error(f'You cannot change the offer or quantity of an addon on a non-active contract')
        elif has_offer_changed:
            new_offer_version = None
            if offer_version_id:
                offer_verson = AddonOfferVersionGetterService.get_from_user_and_id(user, id=offer_version_id)
                if not offer_verson:
                    raise Error(f'Addon Offer Version #{offer_version_id} not found')
                new_offer_version = offer_verson
            elif offer_code:
                offer = AddonOfferGetterService.get_from_user_and_properties(user, code=offer_code)
                if not offer:
                    raise Error(f'Addon Offer with code {offer_code} not found')
                if not offer.version_for_sales:
                    raise Error(f'Addon Offer with code {offer_code} does not have any version available for sales')
                new_offer_version = offer.version_for_sales
            if new_offer_version:
                addon.offer_version = new_offer_version
            if data.get('quantity_sold'):
                quantity_sold = data.get('quantity_sold')
                try:
                    quantity_sold = Decimal(str(quantity_sold)).normalize()
                except (ValueError, TypeError, DecimalException):
                    raise Error('The quantity_sold must be a valid decimal number.')
                if round(quantity_sold, 2) != quantity_sold:
                    raise Error('The quantity_sold must have only two decimal digits.')
                if not addon.offer_version.offer.allow_decimal_quantities and not float(quantity_sold).is_integer():
                    raise Error('The quantity_sold must be a whole number')
                if round(quantity_sold, 2) == 0:
                    raise Error('The quantity sold must not be zero.')
                addon.quantity_sold = data.get('quantity_sold')
            addon.total_amount = round(addon.quantity_sold*addon.offer_version.price, 2)
            if new_offer_version and contract_offer.type == OfferType.lump_sum and addon.offer_version.offer.type != AddOnType.lump_sum:
                raise Error('You can add lump-sum add-ons only to lump-sum contracts')
            if not cls._is_below_maximum(addon):
                if addon.contract:
                    raise Error(f'Add-on cannot be edited. The contract has reached the maximum add-on extension.')
                if addon.lead:
                    raise Error(f'Add-on cannot be edited. The lead has reached the maximum add-on extension.')
            if addon.lead and addon.lead.offer.type == OfferType.loan and (addon.lead.future_contract_duration-addon.lead.offer.free_credit_at_start) <= 0:
                raise Error('You cannot reduce the duration of the loan more than the original duration')
            #we don't remove lead approval if offer editing is unlocked so that it doesn't revert to awaiting decision before locking
            if addon.lead and addon.lead.offer_editing_locked and addon.lead.status.category == StatusCategory.awaiting_payment and addon.offer_version.offer.need_approval:
                LeadStatusChangeService.remove_lead_approval(addon.lead, user,
                                                             'Automatically Unapproved after add-on modification')

            offer_version = addon.offer_version
            loan_mode = data.get('loan_mode', addon.loan_mode)
            if offer_version.offer.type in [AddOnType.loan, AddOnType.deposit_change]:
                if not offer_version.offer.loan_mode:
                    if loan_mode:
                        addon.loan_mode = loan_mode
                    else:
                        raise Error('Loan extension option is required')
                else:
                    addon.loan_mode = offer_version.offer.loan_mode
            elif offer_version.offer.type == AddOnType.lump_sum:
                addon.loan_mode = ''

        if addon.offer_version.offer.linked_to_product and addon.lead and 'device_serial' in data: # contract addons cannot change device
            device = DeviceGetterService.get_device_from_serial_number_only(data['device_serial'], raise_if_absent=True)
            cls._validate_device_type_compatibility(device, addon.offer_version)
            addon.device = device
        
        if data.get('note'):
            note = data.get('note')
            addon.note = str(note) if not isinstance(note, str) else note
        parsed_planned_delivery_date = parse_datetime(data.get('planned_delivery_date'))
        if parsed_planned_delivery_date:
            validate_planned_delivery_dates(parsed_planned_delivery_date, user)
            if not skip_hook:
                cls.send_data_to_hook_delivery_date_change(addon,user, addon.planned_delivery_date, parsed_planned_delivery_date)
            addon.planned_delivery_date = parsed_planned_delivery_date
        elif 'planned_delivery_date' in data:
            if not skip_hook:
                cls.send_data_to_hook_delivery_date_change(addon,user, addon.planned_delivery_date, None)
            addon.planned_delivery_date = None

        if addon.lead and not addon.contract:
            cls.update_lead_addons(addon.lead)

    @classmethod
    def _validate_device_type_compatibility(cls, device, offer_version):
            if not device:
                raise Error('Device is required for serialized add-ons')
            if offer_version.offer.product_type and device.type != offer_version.offer.product_type:
                raise Error('Device type is not compatible with add-on offer')
            if offer_version.offer.product_sub_type and device.product_sub_type != offer_version.offer.product_sub_type:
                raise Error('Device model is not compatible with add-on offer')


    @classmethod
    def pay_with_cash(cls, addon, user, note=''):
        if not user.can_access('CollectCashActions', person=(addon.lead or addon.contract.client).person):
            raise Error('Not enough permissions to pay addons in cash')
        try:
            answer, payment = collect_cash(acting_user=user,
                                           paying_client=addon.contract.client,
                                           amount=addon.to_pay, note=note)
            ReconciledPaymentService.create_reconciliation(payment=payment, addon=addon)
        except Error as e:
            if 'CASH_COLLECTION_LIMIT_EXCEEDED' in str(e):
                return dict({'success': False, 'status': 'CASH_COLLECTION_LIMIT_EXCEEDED'}, **e.data)
            raise e
        answer += ReconciliationService.get_answer_for_addons(addon.contract, [addon])
        return answer

    @classmethod
    def approve(cls, addon, user, auto_deliver=True, skip_hook=False):
        now = datetime.now()
        if addon.sale_approved_by:
            raise Error(f'Addon [{addon.id}] is not pending approval')
        if addon.offer_version.offer.need_approval and not user.can_access('ApproveAddOns', person=(addon.lead or addon.contract.client).person):
            raise Error(f'Not enough permissions to approve addon {addon.reference}')
        if addon.contract and addon.contract.status in [ContractStatus.defaulted, ContractStatus.cancelled]:
            raise Error(f'Add-on {addon.reference} is on a non-active contract and cannot be approved')
        cls.check_addon_offer_available(addon.offer_version, addon.contract, addon.lead, for_registering=True)
        cls.consistency_checks(addon)
        if addon.contract:
            addon.contract.modified_date = now
        if addon.contract and addon.total_amount and addon.offer_version.offer.type != AddOnType.lump_sum: 
            ContractEventService.create_contract_value_change(addon.contract, user, now, addon)
        if addon.contract and addon.device:
            ContractEventService.create_contract_addon_device_event(
                addon.contract, user, addon, now
            )
        answer = []
        if addon.offer_version.offer.purchasing_addon:
            if addon.contract:
                ContractRepaymentService.give_off_taking_discount(addon.contract, -addon.total_amount, [addon], user)
        elif addon.contract and addon.contract.offer.type != OfferType.lump_sum:
            if (addon.contract.get_outstanding_balance() or 0) + addon.total_amount < 0:
                raise Error(f'Addon [{addon.id}] cannot be approved since the resulting contract will be overpaid.')
            if addon.contract.offer.type == OfferType.loan \
                and addon.contract.offer.maximum_value_extension \
                and addon.contract.offer.maximum_value_extension < addon.contract.get_total_extended() + addon.total_amount \
                and addon.total_amount > 0:
                    raise Error(f'Addon [{addon.id}] cannot be approved. The contract has reached the maximum extension.')
            if addon.loan_mode == AddOnLoanExtensionMode.amount or addon.offer_version.offer.type == AddOnType.loan_duration_change:
                if not addon.repayment_increase:
                    addon.repayment_increase = addon.calculate_current_repayment_increase()
                    ContractEventService.create_contract_reference_price_change(addon.contract, user, now, addon)
            if (addon.offer_version.offer.type == AddOnType.loan_duration_change or addon.loan_mode != AddOnLoanExtensionMode.amount) and addon.offer_version.offer.type != AddOnType.lump_sum:
                ContractEventService.create_contract_duration_change(addon.contract, user, now, addon)
            old_total_to_pay = addon.contract.get_total_value()
            old_reference_payment = addon.contract.reference_price
            old_duration = round(addon.contract.get_total_days_to_ownership() or 0)
            if addon.contract.status == ContractStatus.completed:
                answer = ContractRepaymentService.reactivate_contract(addon.contract, date=now)
            if (addon.contract.reference_price+addon.repayment_increase) < 0:
                raise Error('The add-on cannot be created. The resulting repayment amount of the contract would be negative.')
        addon.sale_approved_by = user
        addon.time_approved = now

        if addon.contract and (auto_deliver or not addon.can_be_delivered()):
            cls.set_delivery_status(addon, user, delivered=True)

        if not skip_hook:
            process_hook.add_hook_after_commit(db, 'addon_approved', addon.get_serialized_object())

        flush()
        if addon.contract and not addon.offer_version.offer.purchasing_addon:
            maturity_date = addon.contract.get_date_of_maturity_without_lateness()
            if addon.offer_version.offer.type == AddOnType.loan:
                if addon.loan_mode == AddOnLoanExtensionMode.amount:
                    answer = [{
                        'status': 'LOAN_PRICING_CHANGE',
                        'total_to_pay': round_if_exists(addon.contract.get_total_value()),
                        'old_total_to_pay': round_if_exists(old_total_to_pay),
                        'minimum_payment': round_if_exists(addon.contract.minimum_payment),
                        'reference_payment': round_if_exists(addon.contract.reference_price),
                        'old_reference_payment': round_if_exists(old_reference_payment),
                        'reference_credit': round(addon.contract.offer.base_price_credit),
                        'duration': round(addon.contract.get_total_days_to_ownership()),
                        'expected_maturity_day': maturity_date.strftime('%d'),
                        'expected_maturity_month': maturity_date.strftime('%m'),
                        'expected_maturity_year': maturity_date.strftime('%Y'),
                    }] + answer
                else:
                    answer = [{
                        'status': 'LOAN_DURATION_CHANGE',
                        'total_to_pay': round_if_exists(addon.contract.get_total_value()),
                        'old_total_to_pay': round_if_exists(old_total_to_pay),
                        'duration': round(addon.contract.get_total_days_to_ownership()),
                        'old_duration': round(old_duration),
                        'minimum_payment': round_if_exists(addon.contract.reference_price),
                        'expected_maturity_day': maturity_date.strftime('%d'),
                        'expected_maturity_month': maturity_date.strftime('%m'),
                        'expected_maturity_year': maturity_date.strftime('%Y'),
                    }] + answer
            elif addon.offer_version.offer.type == AddOnType.loan_duration_change:
                    answer = 0*[{
                        'status': 'LOAN_DURATION_CHANGE_NO_VALUE',
                        'total_to_pay': round_if_exists(addon.contract.get_total_value()),
                        'duration': round(addon.contract.get_total_days_to_ownership()),
                        'old_duration': round(old_duration),
                        'reference_payment': round_if_exists(addon.contract.reference_price),
                        'old_reference_payment': round_if_exists(old_reference_payment),
                        'minimum_payment': round_if_exists(addon.contract.reference_price),
                        'expected_maturity_day': maturity_date.strftime('%d'),
                        'expected_maturity_month': maturity_date.strftime('%m'),
                        'expected_maturity_year': maturity_date.strftime('%Y'),
                    }] + answer
            if answer:
                MessageService.send_answer_to_person(answer, addon.contract.client.person)
            if ContractRepaymentService.amount_is_sufficient_for_completion(addon.contract, 0):
                ContractRepaymentService.finish_contract(addon.contract, now)

    @classmethod
    def delete_from_object_and_user(cls, object, user, skip_log=False, **kwargs):
        return cls.delete_addon(object, user)

    @classmethod
    def cancel(cls, addon, user, time_canceled=None, skip_hook=False):
        if addon.cancelled:
            raise Error(f'Add-on [{addon.reference}] is already cancelled')
        if not user.can_access('CancelAddOns', person=(addon.lead or addon.contract.client).person):
            raise Error('INSUFFICIENT_PERMISSION', permission='CancelAddOns')
        if addon.onloan and addon.contract and cls.get_repayment_pricing_after_canceling_add_on(cancelled_add_on=addon) <= 0:
            raise Error('The add-on cannot be cancelled. The repayment amount of the contract would be negative or 0.')    
        if addon.onloan and (addon.total_amount-addon.already_paid) > addon.contract.get_outstanding_balance():
            raise Error(f'Add-on [{addon.reference}] cannot be cancelled because its value is more than the contract outstanding value')
        now = datetime.now()
        if not addon.contract:
            return cls.delete_addon(addon, user)
        if addon.offer_version.offer.type in [AddOnType.deposit_change, AddOnType.loan_duration_change]:
            raise Error(f'Add-on [{addon.reference}] cannot be cancelled because it is a contract terms change add-on. Please use other contract terms change add-ons if you want to modify the contract terms.')
        if addon.offer_version.downpayment and addon.lead and addon.already_paid:
            raise Error(f'Add-on [{addon.reference}] cannot be cancelled because it is linked to the downpayment. Please reverse the downpayment before in order to to cancel this add-on.')
        if addon.onloan and addon.contract:
            cls.update_future_addons_repayment_increase(cancelled_add_on=addon)
        addon.time_canceled = time_canceled or now
        for reconciled in addon.reconciled_payments.select(lambda r: not r.converse):
            ReconciledPaymentService.revert(reconciled, time=time_canceled or now)
        for repayment in addon.repayments.select(lambda r: not r.converse):
            ContractRepaymentService.reverse_repayment(repayment, user, cancelling=True)
        if addon.offer_version.offer.type != AddOnType.lump_sum and addon.sale_approved_by:
            cls.create(
                addon.contract,
                addon.offer_version,
                -addon.quantity_sold,
                user,
                loan_mode=addon.loan_mode,
                reference=addon.reference + 'C',
                cancelled_addon=addon,
                skip_hook=skip_hook,
                delivered=False
            )
        addon.canceled_by = user
        if addon.loan_mode == AddOnLoanExtensionMode.amount:
            ContractEventService.create_contract_reference_price_change(
                addon.contract, user, now, addon)
        elif addon.loan_mode == AddOnLoanExtensionMode.duration:
            ContractEventService.create_contract_duration_change(addon.contract, user, now, addon)
        if ContractRepaymentService.amount_is_sufficient_for_completion(addon.contract, 0):
            ContractRepaymentService.finish_contract(addon.contract, now)
        # We use the general service to mark as not delivered but in cancel mode
        cls.set_delivery_status(addon, user, delivered=False, cancelling=True)
        if not skip_hook:
            process_hook.add_hook_after_commit(db, 'addon_cancelled', addon.get_serialized_object())

    @classmethod
    def check_addon_offer_available(cls, offer_version, contract=None, lead=None, for_registering=False, duplicating=False):
        
        contract_offer = (contract or lead).offer
        available = offer_version.available_for_sales if not for_registering else offer_version.available_for_registration
        village = (lead or contract.client).person.village
        available_entities = offer_version.offer.entities_allowed_for_leads if not for_registering else offer_version.offer.entities_allowed_for_contracts
        entity_names = 'sales' if lead and not for_registering else 'registration'

        if not contract_offer:
            raise Error(f'You cannot add an add-on to a Lead before selecting an offer.')

        if not contract_offer.allow_loan_addons and offer_version.offer.type != AddOnType.lump_sum:
            raise Error(f'The add-on offer {offer_version.offer.name} is not available for {contract_offer.name} because it does not allow loan add-ons.')

        if not duplicating and not available:
            raise Error(f'The add-on offer {offer_version.offer.name} is not available for {entity_names}. ', code="OFFER_NOT_AVAILABLE_FOR_LEADS")
        
        all_available_entities = OperationalEntitiesGetterService.all_descendents_from_entites(available_entities.select())
        if all_available_entities and village not in all_available_entities:
            raise Error(f"Add-on Offer {offer_version.offer.name} is not available in {village.name}. ")

        descendants_categories = select(cat.descendants for cat in contract_offer.addon_offer_categories_allowed)
        if contract_offer.addon_offer_categories_allowed and offer_version.offer.category not in descendants_categories and offer_version.offer.category not in contract_offer.addon_offer_categories_allowed:
            raise Error(f'The add-on offer {offer_version.offer.name} is not available for the contract\'s offer. ')
        

    @classmethod
    def _get_new_reference_for_contract(cls, contract, lead):
        if contract:
            addons = contract.add_ons
            ref = contract.reference
        else:
            addons = lead.addons
            ref = lead.future_contract_reference
        if not addons:
            return ref + "-A0"
        last_ref = max([int(r.split("-A")[1].replace('C','')) for r in select(a.reference for a in addons)])
        return ref + "-A" + str(last_ref+1)

    @classmethod
    def _is_below_maximum(cls, addon):
        total_amount = round(addon.quantity_sold*addon.offer_version.price, 2)
        if addon.contract and addon.offer_version.offer and addon.offer_version.offer.type == AddOnType.loan:
            new_amount = addon.contract.get_total_extended() + total_amount
            old_addon = addon.contract.add_ons.filter(lambda a: a.id == addon.id).first()
            if old_addon:
                new_amount = new_amount - old_addon.total_amount
            if addon.contract.offer.maximum_value_extension and addon.contract.offer.maximum_value_extension < new_amount:
                return False
        if addon.lead and addon.offer_version.offer and addon.offer_version.offer.type == AddOnType.loan:
            new_amount = addon.lead.loan_addons_value + total_amount
            old_addon = addon.lead.addons.filter(lambda a: a.id == addon.id).first()
            if old_addon:
                new_amount = new_amount - old_addon.total_amount
            if addon.lead.offer.maximum_value_extension and new_amount > addon.lead.offer.maximum_value_extension:
                return False
        return True

    @classmethod
    def update_lead_addons(cls, lead):
        duration_mode = AddOnLoanExtensionMode.duration
        for addon in lead.addons.order_by(lambda a: a.loan_mode != duration_mode):
            if addon.contract:
                raise Error(f'Cannot update contract addon. ')
            if addon.loan_mode == AddOnLoanExtensionMode.duration and lead.offer.base_price_amount == 0:
                raise Error('It is not possible to have duration extension add-ons on offers with value 0')
            addon.repayment_increase = addon.calculate_current_repayment_increase()
        flush()
        # We double check in case two addons were added at the same time
        for addon in lead.addons.order_by(lambda a: a.loan_mode != duration_mode):
            if addon.loan_mode == AddOnLoanExtensionMode.amount and addon.repayment_increase == 0 and addon.total_amount != 0:
                addon.repayment_increase = addon.calculate_current_repayment_increase()
                if addon.repayment_increase == 0:
                    raise Error(f'Add-on [{addon.reference}] could not be added, as it would have 0 reference pricing increase. ')
        if lead.addons and lead.reference_price < 0 and (lead.offer and lead.offer.type != OfferType.lump_sum):
            raise Error('Unable to save. The new add-ons configuration will lead to a negative reference price.')
        cls.lead_consistency_checks(lead)

    @classmethod
    def delete_addon(cls, addon, user):
        if addon.contract or not addon.lead.can_edit_offer:
            raise Error(f'Addon with reference {addon.reference} cannot be deleted')
        if addon.reconciled_payments.count() > 0:
            raise Error(f'Addon with reference {addon.reference} cannot be deleted before the payment is reverted')
        if addon.lead and not addon.contract:
            EditLeadPermissionChecker.check_permissions(addon.lead, user)
        if addon.lead and addon.lead.offer_editing_locked and addon.lead.status.category == StatusCategory.awaiting_payment and addon.offer_version.offer.need_approval:
            LeadStatusChangeService.remove_lead_approval(addon.lead, user,
                                                        'Automatically Unapproved after add-on deletion')
        lead = addon.lead
        addon.delete()
        flush()
        if lead:
            AddonService.update_lead_addons(lead)

    @classmethod
    def send_data_to_hook_delivery_date_change(cls, addon, approver, old_date, new_date):
        if old_date != new_date:
            lead_id = addon.lead.id if addon.lead else None
            contract = addon.contract if addon.contract else None
            formatted_data = {
                'lead_id': lead_id,
                'contract_reference': contract.reference if contract else None,
                'acting_user_id': approver.id,
                'device_serial_number': contract.linked_device.get_display_name() if contract and contract.linked_device else None,
                'add_on_reference': addon.reference,
                'old_planned_delivery_date': old_date,
                'new_planned_delivery_date': new_date,
            }
            add_hook_after_commit(db, 'addon_planned_delivery_date_change', formatted_data)

    @classmethod
    def send_data_to_delivery_status_hook(cls, addon):
        add_hook_after_commit(
            db,
            'addon_delivered' if addon.delivered else 'addon_undelivered',
            addon.get_serialized_object()
        )

    @classmethod
    def set_delivery_status(cls, addon, acting_user, delivered, registering=False, skip_hook=False, cancelling=False):

        if not addon.contract:
            raise Error('You can only set an add-on as delivered if it has a contract')

        if cancelling:
            addon.time_canceled = datetime.now()
            addon.canceled_by = acting_user

        if delivered == addon.delivered:
            cls._send_purchasing_addon_activation_if_needed(addon, delivered)
            return
        
        if not registering and delivered and not acting_user.can_access('MarkAsDeliveredAddOns', person=addon.get_person()):
            raise Error('You do not have the permission to mark this addon as delivered')
        
        if not registering and not delivered and not acting_user.can_access('MarkAsUnDeliveredAddOns', person=addon.get_person()):
            raise Error('You do not have the permission to mark this addon as undelivered')

        if not registering and delivered and not addon.delivered and not addon.planned_delivery_date and not acting_user.can_access('MarkAsDeliveredWithoutPlannedDateAddOns', person=addon.get_person()):
            raise Error('You do not have the permission to change the delivery status of this addon because it does not have a planned delivery date')

        addon.delivered = delivered
        addon.delivery_date = datetime.now() if delivered and not registering else None
        if not addon.cancelled_addon:
            if not skip_hook:
                cls.send_data_to_delivery_status_hook(addon)
        
        if not addon.device and addon.offer_version.offer.is_serialized:
            cls._send_purchasing_addon_activation_if_needed(addon, delivered)
            return
        
        origin = SettingsService.get_setting('OriginOfNonSerializedStockItems').get('origin')
        if delivered:
            if addon.offer_version.offer.is_serialized:
                if not StockMovementCreationService.user_can_make_action(addon.device.stock_item, acting_user):
                    raise Error('You cannot link device {device_serial} with client #{client_id}', device_serial=addon.device.composed_serial, client_id=addon.contract.client.id)
                StockMovementCreationService.create(
                    addon.device.stock_item,
                    StockStatus.installed,
                    user=acting_user,
                    destination_client=addon.contract.client,
                    note=f"Add-on {addon.reference} was marked as delivered",
                    manual=False
                )
            if not addon.offer_version.offer.is_serialized and addon.offer_version.offer.linked_to_product:
                if addon.offer_version.offer.purchasing_addon:
                    #create the stockmovement to the client first manually not using the service
                    data = cls.get_non_serialised_movement_data(non_serialised_origin_setting=None, addon=addon, destination=addon.contract.client)
                    cls.forced_purchasing_addon_movement(data, acting_user)
                    #create stockmovement from client to the respective origin
                    data = cls.get_non_serialised_movement_data(non_serialised_origin_setting=origin, current_user=acting_user, addon=addon, destination=addon.contract.client, reverse=True)
                    QuantityStockMovementService.add_from_data_and_user(data, user=acting_user)
                else:
                    data = cls.get_non_serialised_movement_data(non_serialised_origin_setting=origin, addon=addon, destination=addon.contract.client)
                    QuantityStockMovementService.add_from_data_and_user(data, user=acting_user)
            # do the stock movement go to the origin  and find the actual stock item and link to the addon using the quantity stock movement service    
            # on canceling invert the origin and destination
        else:
            if addon.offer_version.offer.is_serialized:
                if not StockMovementCreationService.user_can_make_action(addon.device.stock_item, acting_user):
                    raise Error('You cannot link device {device_serial} with client #{client_id}', device_serial=addon.device.composed_serial, client_id=addon.contract.client.id)
                movement_data = cls.get_serialised_reversed_movement_data(non_serialised_origin_setting=origin, addon=addon, current_user=acting_user, cancelling=cancelling)
                StockMovementCreationService.add_from_data_and_user(movement_data, user=acting_user)
                #create the event for the contract addon device removal 
                ContractEventService.create_contract_addon_device_removal_event(addon.contract, acting_user, addon)
                addon.device = None

            if not addon.offer_version.offer.is_serialized and addon.offer_version.offer.linked_to_product:
                # Since for quantity movement we always use the setting, cancelling or mark as undelivered does the same
                if addon.offer_version.offer.purchasing_addon:
                    data = cls.get_non_serialised_movement_data(non_serialised_origin_setting=origin, current_user=acting_user, addon=addon, destination=addon.contract.client, note=f"Add-on {addon.reference} was marked as undelivered")
                    QuantityStockMovementService.add_from_data_and_user(data, user=acting_user)
                else:
                    data = cls.get_non_serialised_movement_data(non_serialised_origin_setting=origin, current_user=acting_user, addon=addon, destination=addon.contract.client, note=f"Add-on {addon.reference} was marked as undelivered", reverse=True)
                    QuantityStockMovementService.add_from_data_and_user(data, user=acting_user)

        cls._send_purchasing_addon_activation_if_needed(addon, delivered)

    @classmethod
    def _send_purchasing_addon_activation_if_needed(cls, addon, delivered):
        if not delivered or not addon.offer_version.offer.purchasing_addon:
            return
        if not addon.contract or not addon.contract.linked_device:
            return
        pending_repayments = addon.repayments.select(lambda r: not r.converse and not r.processed)[:]
        if not pending_repayments:
            return
        answer = ReconciliationService._generate_activation_answer_if_possible(
            addon.contract,
            pending_repayments
        )
        if answer:
            MessageService.send_answer_to_person(answer, addon.contract.client.person)


    @classmethod
    def get_repayment_pricing_after_canceling_add_on(cls, cancelled_add_on):
        addon_cancelled = ContractAddOn.get(id=cancelled_add_on.id)
        if not addon_cancelled:
            raise Error('ContractAddOn with id %d not found when cancelling' % cancelled_add_on.id)

        # Reference Pricing Before the addon being cancelled was added
        current_reference_pricing = addon_cancelled.contract.reference_price
        new_reference_pricing = current_reference_pricing
        
        # Addons Approved After the addon being cancelled
        addons_approved_after = addon_cancelled.contract.add_ons \
                            .filter(lambda a: a.time_approved > addon_cancelled.time_approved \
                                    and a.excluded_effects_at(addon_cancelled.time_approved) \
                                    and a.loan 
                            )
        
        for addon in addons_approved_after:
            addon_repayment_increase = addon.calculate_current_repayment_increase(excluded_addon_ids=[cancelled_add_on.id])
            new_reference_pricing += addon_repayment_increase 

        return new_reference_pricing
    
    @classmethod
    def update_future_addons_repayment_increase(cls, cancelled_add_on):
        # Addons Approved After the addon being cancelled
        add_ons_approved_after = cancelled_add_on.contract.add_ons \
                            .filter(lambda a: a.time_approved > cancelled_add_on.time_approved \
                                    and a.excluded_effects_at(cancelled_add_on.time_approved) \
                                    and a.loan 
                            )
        
        for add_on in add_ons_approved_after:
            addon_repayment_increase = add_on.calculate_current_repayment_increase(excluded_addon_ids=[cancelled_add_on.id])
            add_on.repayment_increase = addon_repayment_increase

    @classmethod
    def get_available_quantity_at_delivery_origin(cls, addon):
        offer = addon.offer_version.offer
        if not offer.linked_to_product or offer.is_serialized or not offer.product_sub_type:
            return None

        origin_setting = SettingsService.get_setting('OriginOfNonSerializedStockItems').get('origin')
        product_sub_type = offer.product_sub_type
        location = None

        if origin_setting == 'orphaned':
            location = QuantityStockLocation.get(
                product_sub_type=product_sub_type,
                status=StockStatus.orphaned,
                user=None,
                operational_entity=None,
                client=None,
                addon=None,
            )
        elif origin_setting == 'user':
            stock_user = addon.lead.reporter if addon.lead else (
                addon.contract.lead.reporter if addon.contract and addon.contract.lead else None
            )
            if stock_user:
                location = QuantityStockLocation.get(
                    product_sub_type=product_sub_type,
                    status=StockStatus.with_user,
                    user=stock_user,
                    operational_entity=None,
                    client=None,
                    addon=None,
                )
        elif origin_setting == 'operational-entities':
            level = int(SettingsService.get_setting('OriginOfNonSerializedStockItems').get('level'))
            person = addon.lead.person if addon.lead else addon.contract.client.person
            entity = person.village
            while entity and entity.level != level:
                entity = entity.parent
                if not entity:
                    break
            if entity:
                location = QuantityStockLocation.get(
                    product_sub_type=product_sub_type,
                    status=StockStatus.in_stock,
                    user=None,
                    operational_entity=entity,
                    client=None,
                    addon=None,
                )

        return location.available_total_quantity if location else 0

    @classmethod
    def get_non_serialised_movement_data(cls, non_serialised_origin_setting, addon, destination, reverse=False, current_user=None, note=''):
        product_subtype_id = addon.offer_version.offer.product_sub_type.id
        
        # Use the provided note if it's not an empty string; otherwise, use the default based on origin setting
        if not note:
            note = ''  # Default note value, adjust as needed
        else:
            note = note  # Custom note provided by the caller

        STOCK_MOVED_USER_TO_CLIENT = 'Stock moved from user to client.'
        STOCK_MOVED_FROM_ORPHANED_TO_CLIENT = 'Stock moved from orphaned state to client.'
        STOCK_MOVED_BETWEEN_ENTITY_AND_CLIENT = 'Stock moved between operational entity and client.'
        
        # Create the result dictionary
        movement_data = {}
        # Generate data based on non_serialised_origin_setting
        if non_serialised_origin_setting == 'user':
            if reverse:
                user = current_user
            else:
                if addon.contract:
                    user = addon.contract.lead.reporter
                else:
                    user = addon.lead.reporter
            origin = {'status': 'with_user', 'user_id': user.id}
            destination = {'status': 'installed', 'client_id': destination.id}
            if not note:  # If no custom note is provided, set the default
                note = STOCK_MOVED_USER_TO_CLIENT

        elif non_serialised_origin_setting == 'operational-entities':
            level = int(SettingsService.get_setting('OriginOfNonSerializedStockItems').get('level'))
            entity = addon.contract.client.person.village
            # Check if the entity's level matches the configured level
            while entity and entity.level != level:
                entity = entity.parent
                if not entity:
                    break
            origin = {'status': 'in_stock', 'entity_id': entity.id}
            destination = {'status': 'installed', 'client_id': destination.id}
            if not note:  # If no custom note is provided, set the default
                note = STOCK_MOVED_BETWEEN_ENTITY_AND_CLIENT

        elif non_serialised_origin_setting == 'orphaned':
            origin = {'status': 'orphaned'}
            destination = {'status': 'installed', 'client_id': destination.id}
            if not note:  # If no custom note is provided, set the default
                note = STOCK_MOVED_FROM_ORPHANED_TO_CLIENT

        if reverse:
            origin, destination = destination, origin
            if not note or note in [STOCK_MOVED_USER_TO_CLIENT, STOCK_MOVED_BETWEEN_ENTITY_AND_CLIENT, STOCK_MOVED_FROM_ORPHANED_TO_CLIENT]:
                note = f'Reversal: This is Automatic reversal on cancellation'

        # If non_serialised_origin_setting is provided, include origin; otherwise, omit origin
        if non_serialised_origin_setting is not None:
            movement_data = {
                'product_sub_type_id': product_subtype_id,
                'quantity': int(addon.quantity_sold),  # Assuming `addon.quantity_sold` gives the quantity to move
                'note': note,
                'destination': destination,
                'origin': origin
            }
        else:
            movement_data = {
                'product_sub_type_id': product_subtype_id,
                'quantity': int(addon.quantity_sold),  # Assuming `addon.quantity_sold` gives the quantity to move
                'note': "Marking Creation of an Item",
                'destination': {'status': 'installed', 'client_id': destination.id},
            }

        # Return the structured data for stock movement
        return movement_data

    @classmethod
    def get_serialised_reversed_movement_data(cls, non_serialised_origin_setting, addon, current_user=None, note='', cancelling=False):
        stock_item = addon.device.stock_item if addon.device else None
        if cancelling:
            # For cancellation, we want to revert to the previous state before the add-on was delivered
            previous_movement = stock_item.last_movement.previous
            # Create data structure for StockMovementCreationService
            serialised_data = {
                'stock_item_id': stock_item.id,
                'destination_status': previous_movement.destination_status,
                'note': note if note else f"[Automatic] Cancellation of add-on {addon.reference}",
                'manual': False
            }
            # Set the appropriate destination based on the previous movement
            if previous_movement.destination_user:
                serialised_data['destination_user_id'] = previous_movement.destination_user.id
            elif previous_movement.destination_client:
                serialised_data['destination_client_id'] = previous_movement.destination_client.id
            elif previous_movement.destination_entity:
                serialised_data['destination_entity_id'] = previous_movement.destination_entity.id
        else:
            # For marking as undelivered (not cancelling), use the origin setting similar to non-serialized items
            serialised_data = {
                'stock_item_id': stock_item.id,
                'note': note if note else f"Add-on {addon.reference} was marked as undelivered",
                'manual': False
            } 
            # Use the origin setting to determine where to move the item
            if non_serialised_origin_setting == 'user':    
                serialised_data['destination_status'] = 'with_user'
                serialised_data['destination_user_id'] = current_user.id
            elif non_serialised_origin_setting == 'operational-entities':
                # Move to the appropriate operational entity based on level
                level = int(SettingsService.get_setting('OriginOfNonSerializedStockItems').get('level'))
                entity = addon.contract.client.person.village     
                # Find the entity at the correct level
                while entity and entity.level != level:
                    entity = entity.parent
                    if not entity:
                        break
                    
                serialised_data['destination_status'] = 'in_stock'
                serialised_data['destination_entity_id'] = entity.id
            elif non_serialised_origin_setting == 'orphaned':
                # Move to orphaned status
                serialised_data['destination_status'] = 'orphaned'
            else:
                # Default to moving to the current user if no valid setting
                serialised_data['destination_status'] = 'with_user'
                serialised_data['destination_user_id'] = current_user.id
        return serialised_data

    @classmethod
    def forced_purchasing_addon_movement(cls, data, acting_user):
        product_sub_type = ProductSubTypeService.extract_from_user_and_id(
            acting_user, data, "product_sub_type_id", empty_allowed=False
        )


        destination_data = data.get('destination')
        destination = QuantityStockMovementService._get_stock_item(acting_user, product_sub_type, destination_data, 'destination')
        movement = QuantityStockMovement(
                date=datetime.now(),
                user=acting_user,
                note=data.get("note", ""),
                quantity=data.get("quantity", ""),
                destination=destination,
                approval_status=StockMovementStatus.accepted
            )
        return movement