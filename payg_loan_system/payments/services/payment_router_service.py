from payg_loan_system.contracts.models.contract_model import Contract
from payg_loan_system.contracts.models.contract_status import ContractStatus
import re
from pony import orm
from payg_loan_system.contracts.services.contract_repayment_service import ContractRepaymentService

from payg_loan_system.payments.models.payment import Payment
from payg_loan_system.payments.models.wallet import PaymentWallet
from payg_loan_system.contracts.models.addons_model import ContractAddOn
from payg_loan_system.payments.services.payment_creation_service import PaymentCreationService
from payg_loan_system.payments.services.payment_processor_service import PaymentProcessorService
from core_system.phone_numbers.services.phone_number_getter import PhoneNumberGetterService
from shared.logger.loggers import AcceptedWithProcessingError, AlreadyExistsError, LogAPI, Error
from shared.services.settings_service import SettingsService
from shared.api_helpers.hook_helpers.process_hook import process_hook
from sales_system.leads.services.lead_getter_service import LeadGetterService


class PaymentRouterService:

    @classmethod
    def handle_payment(cls, reference, amount, sent_datetime, sender_name, sender_phone_number='',
                       memo='', wallet_operator='', country='', currency=''):
        LogAPI.Event('Payment received. ')

        existing = cls.already_existing_payment(reference, wallet_operator)
        if existing:
            try:
                if not existing.processed:
                    cls.route_payment(existing)
                else:
                    contracts = orm.select(rc.repayment.contract for rc in existing.reconciled_payments if not rc.repayment.processed)
                    for contract in contracts:
                        contract = Contract.get(id=contract.id) # needed cause we are handling exceptions inside the processing function, to avoid db_session ended errors
                        ContractRepaymentService.process_contract_with_unprocessed_repayments(contract)
            except Exception as error:
                orm.rollback()
                LogAPI.Fatal(error)
                # Recalculate cached_remaining_positive after rollback to ensure it's correct
                # This is important when device cloud fails and reconciliation was partially committed
                with orm.db_session:
                    existing = Payment.get(id=existing.id)
                    existing.payment_or_reconciled_changed()
                    serialized_payment = existing.get_serialized_object()
                raise AcceptedWithProcessingError(serialized_payment)
            raise AlreadyExistsError(existing.get_serialized_object())

        incoming_payment = PaymentCreationService.create_payment(
            reference, amount, sent_datetime, sender_name, sender_phone_number,
            memo, wallet_operator, country, currency
        )
        try:
            cls.route_payment(incoming_payment)
        except Exception as error:
            orm.rollback()
            LogAPI.Fatal(error)
            # Recalculate cached_remaining_positive after rollback to ensure it's correct
            # This is important when device cloud fails and reconciliation was partially committed
            with orm.db_session:
                incoming_payment = Payment.get(id=incoming_payment.id)
                incoming_payment.payment_or_reconciled_changed()
                serialized_payment = incoming_payment.get_serialized_object()
            raise AcceptedWithProcessingError(serialized_payment) from error
        return incoming_payment

    @classmethod
    @orm.db_session
    def already_existing_payment(cls, reference, wallet_operator):
        if wallet_operator and Payment.get(Reference=reference.strip(), wallet_operator=''):
            raise Error(f'There is already a payment with transaction ID {reference} but the wallet operator is empty. Duplicated transaction ID are only allowed if both wallet operators are set and different')
        p = Payment.select(lambda p: p.Reference == reference.strip() and p.wallet_operator).first()
        if not wallet_operator and p:
            raise Error(f'There is already a payment with transaction ID {reference} but the wallet operator is {p.wallet_operator}. Duplicated transaction ID are only allowed if both wallet operators are set and different')
        return Payment.get(Reference=reference.strip(), wallet_operator=wallet_operator)

    @classmethod
    def route_payment(cls, payment, reprocessing=False, error_handler=None):
        # Lock the wallet row before any payment/wallet write so concurrent
        # payments for the same wallet serialize instead of deadlocking on the
        # payment<->wallet row locks (see PaymentWallet.lock_row).
        PaymentWallet.lock_row(payment.PaymentWallet.id)
        if not cls.validate_routing(payment, reprocessing):
            return
        target = cls.find_payment_route(payment)

        answer = None
        if target:
            answer = PaymentProcessorService.process_payment_for_target(payment, target, reprocessing, error_handler=error_handler)
        elif not reprocessing:
            # We notify that we dont know what to do with the payment only if not reprocessing
            PaymentProcessorService.process_orphaned_payment(payment)
        # In all cases we notify the payment if not reprocessing
        # We do so AFTER processing to ensure proper status in the hook
        if not reprocessing:
            with orm.db_session:
                payment = Payment.get(id=payment.id)
                process_hook('new_payment', payment.get_serialized_object())
        return answer

    @classmethod
    def _get_routing_rules(cls):
        return SettingsService.get_setting('FlexiblePaymentRouterSettings')

    @classmethod
    @orm.db_session
    def validate_routing(cls, payment, reprocessing):
        payment = Payment.get(id=payment.id)
        if reprocessing:
            with_balance_and_cache_updated = (
                payment.PaymentWallet.balance > 0 and
                (payment.orphaned_cached and payment.PaymentWallet.cached_balance_positive)
            )
            LogAPI.check_and_warn(
                with_balance_and_cache_updated,
                f'Payment [{payment.id}] was sent for routing even though the balance is empty.'
            )
        if payment.processed and not payment.orphaned and payment.orphaned_cached:
            return False
        return True

    @classmethod
    @orm.db_session
    def find_payment_route(cls, payment):
        routing_rules = cls._get_routing_rules()
        sorted_routing_rules = sorted(routing_rules)

        for routing_rule_id in sorted_routing_rules:
            routing_rule = routing_rules[routing_rule_id]
            attribute_value = cls._get_routing_attribute_value(routing_rule['routing_attribute'], payment)
            if attribute_value:
                cleaned_value = cls._check_and_clean_attribute_value(routing_rule, attribute_value)
                cleaned_value = cls._prepend_append_value(routing_rule, cleaned_value)
                if cleaned_value is not False:
                    target = cls._get_target_from_matching_parameter_and_value(
                        routing_rule['matching_parameter'],
                        attribute_value=cleaned_value,
                        strict=routing_rule.get('strict', True),
                        ignore_prefix=routing_rule.get('ignore_prefix', False)
                    )
                    if target:
                        return target
        return None

    @classmethod
    def _check_and_clean_attribute_value(cls, routing_rule, attribute_value):
        if not routing_rule.get('validity_check') or not attribute_value:
            return attribute_value
        else:
            check_mode = routing_rule.get('validity_check_mode', 'FIND_MATCH')
            matches = re.findall(routing_rule['validity_check'], str(attribute_value))
            if matches:
                if check_mode == 'EXTRACT_MATCH':
                    return matches[0]
                return attribute_value
            return False

    @classmethod
    def _prepend_append_value(cls, routing_rule, attribute_value):
        prepend = routing_rule.get('prepend', '')
        append = routing_rule.get('append', '')
        if prepend or append:
            return prepend + str(attribute_value) + append
        return attribute_value

    @classmethod
    def _get_routing_attribute_value(cls, attribute_name, payment, unkown_fails=False):
        if attribute_name == 'wallet_name':
            return payment.PaymentWallet.FullName
        elif attribute_name == 'wallet_linked_client':
            if payment.PaymentWallet.client:
                return payment.PaymentWallet.client.person.id
            elif payment.PaymentWallet.lead:
                return payment.PaymentWallet.lead.person.id
            else:
                return None
        elif attribute_name == 'wallet_linked_user':
            return getattr(payment.PaymentWallet.user, 'id', None)
        elif attribute_name == 'wallet_phone_number':
            if payment.PaymentWallet.phone_number:
                return payment.PaymentWallet.phone_number.number
        elif attribute_name == 'memo':
            return payment.memo if payment.memo != '' else None
        elif unkown_fails:
            raise Exception('Routing attribute not known.')
        return None

    @classmethod
    def _get_target_from_matching_parameter_and_value(cls, matching_parameter, attribute_value, strict, unkown_fails=False, ignore_prefix=False):
        if matching_parameter == 'contract_reference':
            return cls._match_contract_reference(attribute_value, strict)
        elif matching_parameter == 'contract_client':
            return cls._get_target_from_person_if_one(attribute_value)
        elif matching_parameter == 'contract_owner_phone_number':
            return cls._match_contract_owner_phone_number(attribute_value, strict)
        elif matching_parameter == 'user_phone_number':
            return cls._match_user_phone_number(attribute_value, strict)
        elif matching_parameter == 'contract_device_serial_number' or matching_parameter == 'pre_registered_device_sn':
            return cls._match_device_serial_number(attribute_value, strict, ignore_prefix=ignore_prefix)
        elif matching_parameter == 'addon_reference':
            return cls._match_addon_reference(attribute_value, strict)
        elif matching_parameter == 'custom_id':
            return cls._match_custom_id(attribute_value, strict)
        elif unkown_fails:
            raise Exception('Routing attribute not known.')
        else:
            return None
        
    @classmethod
    def _get_eligible_contracts(cls):
        forbidden_statuses = [ContractStatus.defaulted, ContractStatus.cancelled]
        if not SettingsService.get_setting('AllowPaymentsFromPausedContractsAsPending'):    
            forbidden_statuses.append(ContractStatus.paused)
        return Contract.select(lambda c: c.status not in forbidden_statuses)

    @classmethod
    def _match_contract_reference(cls, attribute_value, strict):
        # We get contracts
        contracts = cls._get_eligible_contracts()
        if strict:
            contracts = contracts.filter(lambda c: c.reference == str(attribute_value))
        else:
            contracts = contracts.filter(lambda c: str(attribute_value).lower() in c.reference.lower())
        # We also search for leads
        leads = LeadGetterService.get_leads_ready_for_payment()
        if strict:
            leads = leads.filter(lambda lead: lead.future_contract_reference == str(attribute_value))
        else:
            leads = leads.filter(lambda lead: str(attribute_value).lower() in lead.future_contract_reference.lower())
        return cls._get_target_from_leads_contracts_clients(leads, contracts)

    @classmethod
    def _match_contract_owner_phone_number(cls, attribute_value, strict):
        if strict:
            number = PhoneNumberGetterService.get_phone_number(attribute_value)
        else:
            numbers = PhoneNumberGetterService.find_phone_numbers(attribute_value)
            number = numbers.first() if numbers.count() == 1 else None
        if number and number.persons.count() == 1:
            return cls._get_target_from_person_if_one(number.persons.select().first().id)
        return None

    @staticmethod
    def _match_user_phone_number(attribute_value, strict):
        if strict:
            number = PhoneNumberGetterService.get_phone_number(attribute_value)
        else:
            numbers = PhoneNumberGetterService.find_phone_numbers(attribute_value)
            number = numbers.first() if numbers.count() == 1 else None
        return number.persons.select().first().user if number and number.persons.count() == 1 else None

    @classmethod
    def _match_device_serial_number(cls, attribute_value, strict, ignore_prefix=False):
        # We get the contracts
        contracts = cls._get_eligible_contracts()
        if strict:
            if not ignore_prefix:
                fallback = SettingsService.get_setting('FallBackDeviceType')
                contracts = contracts.filter(lambda c: c.linked_device.composed_serial in [attribute_value, fallback + '-' + attribute_value])
            else:
                contracts = contracts.filter(lambda c: c.linked_device.SerialNumber == attribute_value)
        else:
            contracts = contracts.filter(lambda c: attribute_value.lower() in c.linked_device.composed_serial.lower())
        # We also search for leads (assigned device)
        leads = LeadGetterService.get_leads_ready_for_payment()
        if strict:
            if not ignore_prefix:
                fallback = SettingsService.get_setting('FallBackDeviceType')
                leads = leads.filter(lambda lead: lead.allocated_device.composed_serial in [str(attribute_value), fallback + '-' + str(attribute_value)])
            else:
                leads = leads.filter(lambda lead: lead.allocated_device.SerialNumber == str(attribute_value))
        else:
            leads = leads.filter(lambda lead: str(attribute_value).lower() in lead.allocated_device.composed_serial.lower())
        return cls._get_target_from_leads_contracts_clients(leads, contracts)

    @classmethod
    def _match_addon_reference(cls, attribute_value, strict):
        addons = orm.select(a for a in ContractAddOn if a.unpaid and not a.pending and a.contract in cls._get_eligible_contracts())
        if strict:
            addons = addons.filter(lambda a: str(attribute_value) == a.reference)
        else:
            addons = addons.filter(lambda a: str(attribute_value).lower() in a.reference.lower())
        if addons.count() == 1:
            return addons.first()

    @classmethod
    def _match_custom_id(cls, custom_id, strict):
        # We get the contracts
        contracts = cls._get_eligible_contracts()
        if strict:
            contracts = contracts.filter(lambda a: str(custom_id) == a.client.person.custom_id)
        else:
            contracts = contracts.filter(lambda c: str(custom_id).lower() in c.client.person.custom_id.lower())
        # We also get the leads
        leads = LeadGetterService.get_leads_ready_for_payment()
        if strict:
            leads = leads.filter(lambda lead: lead.person.custom_id == str(custom_id))
        else:
            leads = leads.filter(lambda lead: str(custom_id).lower() in lead.person.custom_id.lower())
        return cls._get_target_from_leads_contracts_clients(leads, contracts)

    @classmethod
    def _get_target_from_person_if_one(cls, person_id):
        if person_id and isinstance(person_id, int):
            contracts = cls._get_eligible_contracts()
            contracts = contracts.filter(lambda c: c.client.person.id == person_id and c.status in [ContractStatus.active, ContractStatus.late])
            leads = LeadGetterService.get_leads_ready_for_payment()
            leads = leads.filter(lambda lead: lead.person.id == person_id)
            return cls._get_target_from_leads_contracts_clients(leads, contracts)
        return None
    
    @classmethod
    def _get_target_from_leads_contracts_clients(cls, leads=None, contracts=None, clients=None):
        # The order of priority is: Contracts, Leads, Add-Ons of Completed Contract, Pending on client of completed contract
        # We split completed and not completed contracts
        completed_contracts = contracts.filter(lambda c: c.status == ContractStatus.completed)
        contracts = contracts.filter(lambda c: c.status != ContractStatus.completed)
        # If only one contract, that takes priority
        if contracts.count() == 1:
            return contracts.first()
        # If no contract, but the client to whom the contract belongs has more contract, then we take those
        elif orm.select(c.client for c in contracts).count() == 1:
            late_contracts = contracts.filter(lambda c: c.status == ContractStatus.late)
            if late_contracts.count() == 1:
                return late_contracts.first()
            active_contracts = contracts.filter(lambda c: c.status == ContractStatus.active)
            if active_contracts.count() == 1:
                return active_contracts.first()
        # If not, we move to leads, if one lead, we pay it
        if leads.count() == 1:
            return leads.first()
        # If not, we check unpaid contract addons 
        # (on completed contract, since if there were active contracts it would have been processed already)
        if completed_contracts.count() != 0:
            completed_contracts = completed_contracts.order_by(orm.desc(Contract.id)) # We take the most recent first
            for completed_contract in completed_contracts:
                # If any completed contract has unpaid addon, 
                # we return it so that money gets reconciled to the unpaid addons on it
                if completed_contract.unpaid_addons.count() != 0:
                    return completed_contract
            # If no unpaid addons on completed contract, we check the setting
            # If we allow pending payments on completed contract, we return the first contract 
            # (it doesn't really matter which one since it goes to the client balance)
            if SettingsService.get_setting('AllowPendingPayments'):
                return completed_contracts.first()
            return None