from datetime import datetime
from payg_loan_system.contracts.models.contract_model import Contract
from payg_loan_system.contracts.services.contract_termination_service import ContractTerminationService
from payg_loan_system.contracts.services.contract_event_service import ContractEventService
from payg_loan_system.contracts.models.addons_model import AddOnLoanExtensionMode, AddOnType
from payg_loan_system.contracts.services.addon_service import AddonService

from pony import orm

from core_system.client.models import Client
from core_system.core_entities import db
from core_system.person.models.person_model import PersonType
from payg_loan_system.contracts.models.addons_model import (
    AddOnLoanExtensionMode, AddOnType)
from payg_loan_system.contracts.models.contract_model import Contract
from payg_loan_system.contracts.services.addon_service import AddonService
from payg_loan_system.contracts.services.contract_event_service import \
    ContractEventService
from payg_loan_system.contracts.services.contract_repayment_service import \
    ContractRepaymentService
from payg_loan_system.contracts.services.contract_termination_service import \
    ContractTerminationService
from payg_loan_system.offers.models import OfferType
from sales_system.leads.models.status_category import StatusCategory
from sales_system.leads.services.lead_status_change_service import \
    LeadStatusChangeService
from shared.api_helpers.hook_helpers.process_hook import add_hook_after_commit
from shared.logger.loggers import Error
from shared.services.settings_service import SettingsService
from stock_management_system.services.stock_movement_creation_service import \
    StockMovementCreationService
from stock_management_system.stock_status import StockStatus


class ContractCreationService:

    @classmethod
    def create_from_lead_and_device(cls, lead, device, acting_user,
        contract_mobile_uuid=None, undelivered_addons=None, note=''):
        to_default = lead.person.client and lead.person.client.first_active_or_late_contract
        # We check if everything is ok for registration
        cls._check_if_creation_is_impossible(lead, device, acting_user)

        # We create the client object
        client = cls._create_client_from_lead(lead)
        # We create the contract object
        contract = cls._create_contract_object(
            lead, acting_user, contract_mobile_uuid, undelivered_addons
        )
        # We update the device object (see if that goes into the repayment service)
        cls.link_device_to_contract(device, contract)
        lead.allocated_device = None

        offer = contract.offer
        total_loan_value = contract.get_total_value()
        formatted_data = {
            'client_id': client.id,
            'client_name': client.person.name,
            'client_surname': client.person.surname,
            'contract_reference': contract.reference,
            'lead_id': lead.id,
            'lead_generator_id': lead.generator.id if lead.generator else None,
            'device_serial_number': device.get_display_name() if device else None,
            'total_loan_value': float(total_loan_value) if total_loan_value else None,
            'offer_code': offer.code,
            'offer_type': offer.get_human_readable_type(),
            'acting_user_id': acting_user.id
        }
        add_hook_after_commit(db, 'client_registered', formatted_data)
        # We create the event
        approver = contract.lead.decisionMaker if contract.lead else None
        ContractEventService.create_contract_creation_event(contract, approver, note)
        orm.flush()
        amount_addons = contract.add_ons.select(
            lambda a: a.loan_mode == AddOnLoanExtensionMode.amount
        )
        if amount_addons.count():
            ContractEventService.create_contract_reference_price_change(
                contract, approver, addons=amount_addons
            )
        duration_addons = contract.add_ons.select(
            lambda a: a.loan_mode == AddOnLoanExtensionMode.duration
        )
        if duration_addons.count():
            ContractEventService.create_contract_duration_change(
                contract, approver, addons=duration_addons
            )
        # We create the first repayment
        cls._create_and_link_first_repayment(contract, acting_user)
        # We link the payment account
        cls._link_payment_account(lead, client)
        # We set the lead as installed
        LeadStatusChangeService.update(lead)
        add_hook_after_commit(db, 'lead_edited', lead.get_serialized_object())
        # We sync the device status
        ContractRepaymentService.sync_device_status_from_contract(device, contract)
        if device:
            StockMovementCreationService.create(
                device.stock_item,
                StockStatus.installed,
                user=acting_user,
                destination_client=contract.client,
                note="[Automatic] Registration",
                manual=False
            )

        contract.update_cached_data(force=True)

        answer = {'success': True, 'contract': contract}

        cls._link_survey_answer_to_client(lead,client)

        if to_default and not SettingsService.get_setting('AllowMultipleContracts'):
            ContractTerminationService.default_contract(contract, acting_user)
            answer['error'] = 'REGISTER_ERROR_CLIENT_HAS_ACTIVE_CONTRACT'
        return answer

    @classmethod
    def link_device_to_contract(cls, device, contract):
        if device:
            device.clear()
            device.RegistrationTime = contract.start_time
            device.contract = contract
            device.credit_unit = contract.offer.credit_unit or ''
            device.allocated_lead = None

    @classmethod
    def _create_and_link_first_repayment(cls, contract, acting_user):
        return ContractRepaymentService.create_first_repayment_on_contract(
            contract, acting_user
        )

    @classmethod
    def _link_payment_account(cls, lead, client):
        # We do this in all cases
        for wallet in lead.payment_wallets:
            wallet.client = client
            wallet.lead = None

    @classmethod
    def _create_client_from_lead(cls, lead):
        # We have checked already that the lead does not have a client
        person = lead.person
        if person.client:
            return person.client
        person.type = PersonType.client
        client = Client(
            RegistrationDate=datetime.now(),
            person=person
        )
        orm.flush()  # We flush here to be able to get the new client ID
        return client

    @classmethod
    def _create_contract_object(cls, lead, acting_user, contract_mobile_uuid=None, undelivered_addons=None):
        reference = lead.future_contract_reference
        offer = cls._get_offer(lead)
        # First approve duration addons so they use the original Reference Pricing
        # We don't deliver because we do not yet have the contract
        addons = lead.addons.select(lambda a: not a.sale_approved_by)
        undelivered_addons = [] if not undelivered_addons else undelivered_addons
        for addon in addons.filter(lambda a: a.offer_version.offer.type == AddOnType.loan_duration_change):
            AddonService.approve(addon, acting_user, auto_deliver=False)
        for addon in addons.filter(lambda a: a.offer_version.offer.type in [AddOnType.loan, AddOnType.deposit_change] and a.loan_mode == AddOnLoanExtensionMode.duration):
            AddonService.approve(addon, acting_user, auto_deliver=False)
        for addon in addons.filter(lambda a: a.offer_version.offer.type in [AddOnType.loan, AddOnType.deposit_change] and a.loan_mode == AddOnLoanExtensionMode.amount):
            AddonService.approve(addon, acting_user, auto_deliver=False)
        for addon in addons.filter(lambda a: a.offer_version.offer.type == AddOnType.lump_sum):
            AddonService.approve(addon, acting_user, auto_deliver=False)

        cls.check_contract_terms_consistency(lead)
        now = datetime.now()
        contract = Contract(
            client=lead.person.client,
            reference=reference,
            start_time=now,
            end_time=None,
            offer=offer,
            linked_device=None,
            lead=lead,
            next_repayment_due_time=now,
            portfolio=lead.portfolio
        )
        if contract_mobile_uuid:
            contract.mobile_uuid = contract_mobile_uuid
        contract.add_ons = lead.addons
        for addon in contract.add_ons:
            AddonService.set_delivery_status(
                addon, acting_user, delivered=addon.id not in undelivered_addons, registering=True
            )
        for a in contract.add_ons.filter(lambda a: a.device is not None):
            ContractEventService.create_contract_addon_device_event(contract, acting_user, a, now)
        return contract

    @classmethod
    def _check_if_creation_is_impossible(cls, this_lead, this_device, acting_user):
        if not this_lead.decision or this_lead.discarded:
            raise Error('LEAD_NOT_APPROVED')
        if this_lead.installed:
            raise Error('LEAD_ALREADY_REGISTERED', client_id=this_lead.person.client.id)
        if not this_lead.deposit_paid:
            raise Error('LEAD_INITIAL_PAYMENT_NOT_PAID')
        if not this_lead.offer_editing_locked:
            raise Error('OFFER_EDITING_LOCKED')
        if this_lead.forms_missing_for_registration:
            forms_names = ', '.join([f.name for f in this_lead.forms_missing_for_registration])
            raise Error('FORMS_MISSING_FOR_REGISTRATION', forms_names=forms_names)
        offer = cls._get_offer(this_lead)
        if offer is None:
            raise Error('OFFER_DOES_NOT_EXIST')
        if not offer.in_use:
            raise Error('OFFER_DISABLED')
        if not SettingsService.get_setting('ContractDeviceRestrictions') == 'no_device' and offer.linked_to_product:
            if not this_device.can_use_offer(offer):
                raise Error('DEVICE_NOT_ALLOWED_ON_OFFER')
            if this_device.allocated_lead and this_device.allocated_lead != this_lead:
                raise Error('DEVICE_ALREADY_ALLOCATED', lead_id=this_device.allocated_lead.id)
            if this_device.contract is not None:
                raise Error('DEVICE_ALREADY_REGISTERED', device_owner_id=this_device.contract.client.id)
        if not this_lead.deposit_paid:
            raise Error('LEAD_INITIAL_PAYMENT_NOT_PAID')
        if SettingsService.get_setting('ContractDeviceRestrictions') == 'require_device' and offer.linked_to_product and not this_device.is_compatible_with_offer(offer):
            raise Error(
                'CREDIT_UNIT_NOT_ALLOWED_FOR_DEVICE',
                allowed_units=this_device.get_allowed_units()
            )
        if (this_lead.downpayment < 0 \
            and not offer.base_price_amount_can_be_negative)\
            or (this_lead.offer.can_be_completed \
                and this_lead.maximum_pending < 0 \
                and not offer.base_price_amount_can_be_negative):
            raise Error('CANNOT_REGISTER_LEAD_WITH_WRONG_ADDONS')
        if not StatusCategory.installed in [
            s.category for s in LeadStatusChangeService.get_allowed_statuses_from_lead(
                this_lead, acting_user
            )
        ]:
            raise Error('CANNOT_REGISTER_RESTRICTED_LEAD')

    @classmethod
    def check_contract_terms_consistency(cls, lead):
        if lead.offer.can_be_completed and lead.offer.type != OfferType.lump_sum:
            if lead.offer.base_price_amount_can_be_negative:
                return
            if not lead.future_contract_time_to_pay:
                raise Error('LOAN_WITH_ZERO_DURATION')
            if lead.downpayment >= lead.future_contract_value + lead.lump_sum_addons_value:
                if not (lead.downpayment == lead.future_contract_value + lead.lump_sum_addons_value and lead.offer.base_price_amount_can_be_negative):
                    raise Error('VALUE_LESS_THAN_DEPOSIT')
            calculated_ref_price = lead.future_contract_value_without_deposit/(
                lead.future_contract_time_to_pay/lead.offer.base_price_credit
            )
            if abs(lead.reference_price-calculated_ref_price) > 0.03:
                print(lead.reference_price, calculated_ref_price, abs(lead.reference_price-calculated_ref_price))
                raise Exception('INCONSISTENT_CONTRACT_TERMS')

    @classmethod
    def _get_offer(cls, lead):
        return lead.get_offer()

    @classmethod
    def _link_survey_answer_to_client(cls, lead, client):
        for ans in lead.forms_answered:
            ans.client_answering = client
