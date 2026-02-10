from payg_loan_system.contracts.models.contract_status import ContractStatus
from pony import orm
from payg_loan_system.devices.model.device import Device
from payg_loan_system.payments.models.wallet import PaymentWallet
from payg_loan_system.contracts.services.reconciled_payment_service import ReconciledPaymentService
from core_system.client.models import Client
from core_system.phone_numbers.services.phone_number_getter import PhoneNumberGetterService
from sales_system.leads.models.lead import Lead
from shared.services.settings_service import SettingsService


class PaymentOptionsService:

    @classmethod
    def get_from_device_serial_number(cls, device_serial_number):
        this_device = Device.get(composed_serial=device_serial_number)
        if this_device:
            return cls.get_from_device(this_device)
        return []

    @classmethod
    def get_from_contract_reference(cls, contract_reference):
        this_lead = Lead.get(future_contract_reference=contract_reference)
        if not this_lead:
            return []
        if this_lead.installed:
            client = this_lead.person.client
            return cls.get_from_client(client)
        else:
            return cls.get_from_lead(this_lead)

    @classmethod
    def get_from_client_id(cls, client_id):
        client = Client.get(id=client_id)
        return cls.get_from_client(client)

    @classmethod
    def get_from_payment_account_name(cls, payment_account_name):
        payment_account = PaymentWallet.select(lambda a: a.FullName == payment_account_name)
        if payment_account.count() != 1:
            return []
        payment_account = payment_account.first()
        client = payment_account.client
        if not client:
            return []
        return cls.get_from_client(client)

    @classmethod
    def get_from_phone_number(cls, phone_number):
        client = PhoneNumberGetterService.get_client_by_phone_number(phone_number)
        if client:
            return cls.get_from_client(client)
        leads = PhoneNumberGetterService.get_leads_by_phone_number(phone_number)
        options = []
        if leads:
            for lead in leads:
                options += cls.get_from_lead(lead)
        return options

    @classmethod
    def get_from_client(cls, client):
        if client:
            this_device = orm.select(device for device in Device if device.contract.client == client and device.contract.status == ContractStatus.active).first()
            if this_device:
                return cls.get_from_device(this_device)
        return []

    @classmethod
    def get_from_device(cls, device):
        if device.contract is None:
            return []
        offer = device.contract.offer
        pending = device.contract.pending_amount
        amount_left_to_pay = device.contract.get_outstanding_balance() - pending \
            if device.contract.get_outstanding_balance() is not None else None
        contract_reference = cls.get_contract_reference_from_device(device)
        payment_options = cls._get_payment_options_from_amount_left_to_pay_and_offer(amount_left_to_pay, offer)
        return cls._get_from_options_and_contract(payment_options, contract_reference)

    @classmethod
    def _get_payment_options_from_amount_left_to_pay_and_offer(cls, amount_left_to_pay, offer):
        raw_payment_options = []
        option_1 = cls._get_option_from_pricing_time_and_next_pricing(
            pricing=offer.base_price_amount,
            time=offer.base_price_credit,
            previous_pricing=None,
            next_pricing=offer.discount_price_1_amount,
            amount_left_to_pay=amount_left_to_pay
        )
        if option_1:
            raw_payment_options.append(option_1)
        if offer.discount_price_1_amount:
            option_2 = cls._get_option_from_pricing_time_and_next_pricing(
                pricing=offer.discount_price_1_amount,
                time=offer.discount_price_1_credit,
                previous_pricing=offer.base_price_amount,
                next_pricing=offer.discount_price_2_amount,
                amount_left_to_pay=amount_left_to_pay
            )
            if option_2:
                raw_payment_options.append(option_2)
        if offer.discount_price_2_amount:
            option_3 = cls._get_option_from_pricing_time_and_next_pricing(
                pricing=offer.discount_price_2_amount,
                time=offer.discount_price_2_credit,
                amount_left_to_pay=amount_left_to_pay,
                previous_pricing=offer.discount_price_1_amount,
                next_pricing=None,
            )
            if option_3:
                raw_payment_options.append(option_3)
        return raw_payment_options

    @classmethod
    def _get_option_from_pricing_time_and_next_pricing(cls, pricing, time, next_pricing, amount_left_to_pay,
                                                       previous_pricing):
        max_multiple = cls._get_max_multiple(pricing, next_pricing, amount_left_to_pay, previous_pricing)
        if max_multiple is None or max_multiple > 0:
            option = {
                "pricing_amount": pricing if amount_left_to_pay is None or pricing < amount_left_to_pay else amount_left_to_pay,
                "pricing_period_in_days": int(time),
                "type": 'REPAYMENT',
                "max_multiple": max_multiple,
                "currency": SettingsService.get_setting('CurrencySymbol')
            }
        else:
            option = None
        return option

    @classmethod
    def _get_max_multiple(cls, pricing, next_pricing, amount_left_to_pay, previous_pricing):
        if amount_left_to_pay is None:
            return None
        if amount_left_to_pay <= 0:
            return 0
        if not next_pricing or next_pricing > amount_left_to_pay:
            max_multiple = amount_left_to_pay // pricing
            if previous_pricing is None:
                if (next_pricing and ((max_multiple+1)*pricing < next_pricing)) or max_multiple == 0:
                    max_multiple += 1
        else:
            max_multiple = next_pricing // pricing
            exact_multiple = (max_multiple == (next_pricing / pricing))
            if exact_multiple:
                max_multiple = max_multiple - 1
        return max_multiple

    @classmethod
    def get_contract_reference_from_device(cls, device):
        return device.contract.reference if device.contract else None

    @classmethod
    def get_from_lead(cls, lead):
        contract_reference = str(lead.future_contract_reference)
        payment_options = cls.get_payment_options_for_lead(lead)
        options = cls._get_from_options_and_contract(payment_options, contract_reference)
        return options

    @classmethod
    def get_payment_options_for_lead(cls, lead):
        offer = lead.offer
        if not offer or lead.deposit_paid:
            payment_options = []
        else:
            payment_options = cls._get_initial_payment_pricing_from_offer(offer, lead)
        return payment_options

    @classmethod
    def _get_initial_payment_pricing_from_offer(cls, offer, lead):
        downpayment_amount = offer.registration_fee
        downpayment_amount_remaining = downpayment_amount - lead.already_paid
        free_time_at_start_in_days = round(offer.free_credit_at_start)
        options = [
            {
                "pricing_amount": downpayment_amount_remaining,
                "pricing_period_in_days": free_time_at_start_in_days,
                "type": 'INITIAL_PAYMENT',
                "max_multiple": 1,
                "currency": SettingsService.get_setting('CurrencySymbol')
            }
        ]
        return options

    @classmethod
    def _get_from_options_and_contract(cls, payment_options, contract_reference):
        options = [
            {
                "contract_reference": contract_reference,
                "payment_options": payment_options
            }
        ]
        return options
