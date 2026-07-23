from shared.api_helpers.client_helpers.json_serialization_helpers import serialize_data_to_json
from payg_loan_system.offers.models import OfferType
from shared.logger.loggers import LogAPI
from pony import orm


class ContractCacheService:

    @classmethod
    def update_contract_cache(cls, contract, contract_terms_changed=False, repayment_created=False, volatile=False, force=False):
        contract_terms_changed = contract_terms_changed or contract.contract_terms_cache_update_needed
        repayment_created = repayment_created or contract.contract_repayment_cache_update_needed
        if contract_terms_changed or force:
            cls.update_contract_terms_changed(contract)
        if contract_terms_changed or repayment_created or force:
            cls.update_repayment_created(contract)
            cls.update_percentage_paid(contract)
        if contract.expected_paid_cache_update_needed or contract_terms_changed or repayment_created or force:
            cls.update_expected_paid(contract, force=force or contract_terms_changed)
        if volatile:
            cls.update_volatile(contract)

    @classmethod
    def update_percentage_paid(cls, contract):
        percentage_paid = contract.get_percentage_repaid(cached=False, use_cache=True)
        contract.cached_percentage_paid = round(percentage_paid, 4) if percentage_paid else percentage_paid

    @classmethod
    def update_volatile(cls, contract):
        cumulative_days_late = contract.get_cumulative_days_in_arrears(use_cache=True, cached=False)
        timeliness_ratio = contract.get_timeliness_ratio(use_cache=True, cached=False)
        contract.cached_cumulative_days_late = round(cumulative_days_late, 2) if cumulative_days_late else cumulative_days_late
        contract.cached_timeliness_ratio = round(timeliness_ratio, 2) if timeliness_ratio else timeliness_ratio

    @classmethod
    def update_expected_paid(cls, contract, force=False):
        expected_paid, expected_paid_until = contract.get_expected_amount_repaid(cached=False, include_date_until=True)
        contract.cached_expected_amount_repaid = round(expected_paid, 2) if expected_paid else expected_paid
        contract.cached_expected_amount_repaid_until = expected_paid_until
        if contract.offer.type == OfferType.time_based or force:
            contract.cached_expected_payments_table = serialize_data_to_json(contract.get_expected_payments_table(cached=False))

    @classmethod
    def update_repayment_created(cls, contract, repayment=None):
        # I guess we could technically update directly from the repayment in the future, but let's start safe
        cumulative_amount_repaid = contract.get_cumulative_amount_repaid(cached=False)
        cumulative_amount_discounted = contract.get_amount_discounted(cached=False)
        cumulative_days_late_until_last_payment = contract.get_cumulative_days_in_arrear_until_last_payment(cached=False)
        cumulative_credit_bought = contract.get_credits_bought(cached=False)
        contract.cached_cumulative_amount_repaid = round(cumulative_amount_repaid, 2) if cumulative_amount_repaid else cumulative_amount_repaid
        contract.cached_cumulative_amount_discounted = round(cumulative_amount_discounted, 2) if cumulative_amount_discounted else cumulative_amount_discounted
        contract.cached_cumulative_days_in_arrears_until_last_payment = round(cumulative_days_late_until_last_payment, 2) if cumulative_days_late_until_last_payment else cumulative_days_late_until_last_payment
        contract.cached_cumulative_credit_bought = round(cumulative_credit_bought, 2) if cumulative_credit_bought else cumulative_credit_bought

    @classmethod
    def update_contract_terms_changed(cls, contract):
        total_amount = contract.get_total_value(cached=False)
        total_downpayment = contract.get_total_downpayment(cached=False)
        reference_pricing_increase = contract.addons_price_at(cached=False)
        loan_extension_addon_amount = contract.get_total_extended(cached=False)
        lump_sum_addon_amount = contract.get_total_value_of_lumpsum_addons(cached=False)
        total_days_to_ownership = contract.get_total_days_to_ownership(cached=False)
        contract.cached_total_value = round(total_amount, 2) if total_amount else total_amount
        contract.cached_total_downpayment = round(total_downpayment, 2) if total_downpayment else total_downpayment
        contract.cached_reference_price_increase = round(reference_pricing_increase, 2) if reference_pricing_increase else reference_pricing_increase
        contract.cached_loan_extension_addon_amount = round(loan_extension_addon_amount, 2) if loan_extension_addon_amount else loan_extension_addon_amount
        contract.cached_lump_sum_addon_amount = round(lump_sum_addon_amount, 2) if lump_sum_addon_amount else lump_sum_addon_amount
        contract.cached_total_days_to_ownership = round(total_days_to_ownership, 2) if total_days_to_ownership else total_days_to_ownership
        contract.cached_expected_payments_table = serialize_data_to_json(contract.get_expected_payments_table(cached=False))

    @classmethod
    def check_cache_accuracy(cls, contract, fix_if_needed=False):

        LogAPI.check_and_warn(
            contract.repayments.select(
                lambda r: r.amount == 0 and not r.discount_type and not r.reconciled_payments and not r.contract_event and not r.converse
            ).count() == 0, message='Empty repayments found for '+repr(contract)
        )

        all_good = True
        message = 'Incoherent cache for '+repr(contract)

        if contract.cached_total_value:
            total_amount = contract.get_total_value(cached=False)
            all_good = LogAPI.check_and_warn(
                contract.cached_total_value == round(total_amount, 2), message=message+' - total_value'
            ) and all_good
        if contract.cached_reference_price_increase:
            reference_pricing_increase = contract.addons_price_at(cached=False)
            all_good = LogAPI.check_and_warn(contract.cached_reference_price_increase == round(reference_pricing_increase, 2), message=message+' - reference_price_increase') and all_good
        if contract.cached_loan_extension_addon_amount:
            loan_extension_addon_amount = contract.get_total_extended(cached=False)
            all_good = LogAPI.check_and_warn(contract.cached_loan_extension_addon_amount == round(loan_extension_addon_amount, 2), message=message+' - loan_extension_addon_amount') and all_good
        if contract.cached_lump_sum_addon_amount:
            lump_sum_addon_amount = contract.get_total_value_of_lumpsum_addons(cached=False)
            all_good = LogAPI.check_and_warn(contract.cached_lump_sum_addon_amount == round(lump_sum_addon_amount, 2), message=message+' - lump_sum_addon_amount') and all_good
        if contract.cached_total_days_to_ownership:
            total_days_to_ownership = contract.get_total_days_to_ownership(cached=False)
            all_good = LogAPI.check_and_warn(contract.cached_total_days_to_ownership == round(total_days_to_ownership, 2), message=message+' - total_days_to_ownership') and all_good
        if contract.cached_expected_payments_table:
            expected_payments_table = serialize_data_to_json(contract.get_expected_payments_table(cached=False))
            all_good = LogAPI.check_and_warn(contract.cached_expected_payments_table == expected_payments_table, message=message+' - expected_payments_table') and all_good

        if contract.cached_cumulative_amount_repaid:
            cumulative_amount_repaid = contract.get_cumulative_amount_repaid(cached=False)
            all_good = LogAPI.check_and_warn(contract.cached_cumulative_amount_repaid == round(cumulative_amount_repaid, 2), message=message+' - cumulative_amount_repaid') and all_good
        if contract.cached_cumulative_amount_discounted:
            cumulative_amount_discounted = contract.get_amount_discounted(cached=False)
            all_good = LogAPI.check_and_warn(contract.cached_cumulative_amount_discounted == round(cumulative_amount_discounted, 2), message=message+' - cumulative_amount_discounted') and all_good
        if contract.cached_cumulative_days_in_arrears_until_last_payment:
            cumulative_days_late_until_last_payment = contract.get_cumulative_days_in_arrear_until_last_payment(cached=False)
            all_good = LogAPI.check_and_warn(contract.cached_cumulative_days_in_arrears_until_last_payment == round(cumulative_days_late_until_last_payment, 2), message=message+' - cumulative_days_late_until_last_payment') and all_good

        # Update on repayment received or contract terms change
        if contract.cached_percentage_paid:
            percentage_paid = contract.get_percentage_repaid(cached=False, use_cache=True)
            all_good = LogAPI.check_and_warn(contract.cached_percentage_paid == round(percentage_paid, 4), message=message+' - percentage_paid') and all_good

        if contract.cached_expected_amount_repaid and not contract.expected_paid_cache_update_needed:
            expected_paid, expected_paid_until = contract.get_expected_amount_repaid(cached=False, include_date_until=True)
            all_good = LogAPI.check_and_warn(contract.cached_expected_amount_repaid == round(expected_paid, 2), message=message+' - expected_paid') and all_good
            all_good = LogAPI.check_and_warn(contract.cached_expected_amount_repaid_until == expected_paid_until, message=message+' - expected_paid_until') and all_good

        if contract.cached_total_downpayment:
            total_downpayment = contract.get_total_downpayment(cached=False)
            all_good = LogAPI.check_and_warn(
                contract.cached_total_downpayment == total_downpayment,
                message=message+' - total_downpayment'
            ) and all_good

        if not all_good and fix_if_needed:
            print('Fixing cache for '+repr(contract))
            cls.update_contract_cache(contract=contract, force=True, volatile=True)

    @classmethod
    def get_wallet_lead_reconciliations(cls, wallet):
        return orm.select(r for r in wallet.payment_debits if (r.lead and not r.lead.contract))

    @classmethod
    def wallet_has_balance_with_leads(cls, wallet, amount):
        wp = cls.get_wallet_lead_reconciliations(wallet)
        return orm.sum(r.amount for r in wp) >= amount

    @classmethod
    def remove_wallet_lead_reconciliations(cls, wallet):
        for r in cls.get_wallet_lead_reconciliations(wallet):
            r.delete()