from payg_loan_system.contracts.models.contract_status import ContractStatus
from payg_loan_system.contracts.models.contract_model import Contract
from payg_loan_system.contracts.models.repayment_model import ContractRepayment
from statistics import mean

from pony.orm import db_session
from pony import orm
from shared.services.settings_service import SettingsService
from shared.helpers.date_helper import ninety_days_from_today, hundred_eighty_days_from_today
from payg_loan_system.offers.models import OfferType


class ClientPortfolioStats:

    @db_session
    def active_contract_count(self):
        gogla_active_contracts = self.get_contracts_with_repayments_in_last_90_days()
        return gogla_active_contracts.count()

    @staticmethod
    def get_repayments_in_last_90_days():
        repayments_in_last_90_days = orm.select(repayment for repayment in ContractRepayment
                                                if repayment.time >= ninety_days_from_today())
        return repayments_in_last_90_days

    @staticmethod
    def get_contracts_with_repayments_in_last_90_days():
        repayments_last_90_days = ClientPortfolioStats.get_repayments_in_last_90_days()
        contracts_in_last_90_days = orm.select(repayment.contract for repayment in repayments_last_90_days)
        return orm.select(contract for contract in Contract if contract in contracts_in_last_90_days)

    @staticmethod
    def get_repayments_between_90_and_180_days():
        repayments_in_last_90_days = orm.select(repayment for repayment in ContractRepayment
                                                if repayment.time >= hundred_eighty_days_from_today()
                                                and repayment.time < ninety_days_from_today())
        return repayments_in_last_90_days

    @staticmethod
    def get_contracts_with_repayments_between_90_and_180_days():
        repayments_90_to_180 = ClientPortfolioStats.get_repayments_between_90_and_180_days()
        contracts = orm.select(repayment.contract for repayment in repayments_90_to_180)
        return orm.select(contract for contract in Contract if contract in contracts)

    @db_session
    def get_churn_rate(self):
        contracts_active_previously = self.get_contracts_with_repayments_between_90_and_180_days()
        contracts_active_now = self.get_contracts_with_repayments_in_last_90_days()
        contracts_active_previously_count = contracts_active_now.count()

        churned_contracts = contracts_active_previously.filter(lambda contract:
                                                               contract not in contracts_active_now
                                                               and contract.status != ContractStatus.completed)
        churned_countract_count = churned_contracts.count()

        if contracts_active_previously_count:
            return '{0:.2f}%'.format((churned_countract_count / contracts_active_previously_count) * 100)

        return 0

    @db_session
    def average_customer_deposit_by_cost(self):
        gogla_active_contracts = self.get_contracts_with_repayments_in_last_90_days()
        deposits_by_cost = [self._get_deposit_to_cost_ratio_for_offer(contract.offer) for contract in
                            gogla_active_contracts]

        if deposits_by_cost:
            return '%.2f' % (mean(deposits_by_cost) * 100)

        return 0

    @staticmethod
    def _get_deposit_to_cost_ratio_for_offer(offer):
        if not offer.registration_fee or not offer.unit_cost: 
            return 0
        try:
            return offer.registration_fee / offer.unit_cost
        except Exception as e:
            return 0

    @db_session
    def get_device_compliance_percentage(self):

        gogla_active_contracts = self.get_contracts_with_repayments_in_last_90_days()
        active_contract_count = gogla_active_contracts.count()

        if not active_contract_count:
            return "0.00%"

        compliant_contracts = gogla_active_contracts.filter(lambda contract:
                                                            contract.offer.lighting_global_compliant == True)
        compliant_contracts_count = compliant_contracts.count()

        return "{0:.2f}%".format(compliant_contracts_count / active_contract_count * 100)

    @db_session
    def average_active_clients_credit_period(self):
        gogla_active_contracts = self.get_contracts_with_repayments_in_last_90_days()
        active_contracts_count = gogla_active_contracts.count()

        gogla_active_contracts = gogla_active_contracts.filter(lambda c: c.offer.type == OfferType.loan)
        total_days_to_ownership = orm.sum(contract.offer.time_to_ownership_in_days for contract in gogla_active_contracts)

        if not active_contracts_count or not total_days_to_ownership:
            return "0.00%"

        average_days_to_ownership = float(total_days_to_ownership) / float(active_contracts_count)

        average_years_to_onwership = float(float(average_days_to_ownership) / 7 / 52)

        return '{0:.2f}'.format(average_years_to_onwership)

    def recent_revenue_average(self, start_date, end_date):
        active_contracts = self.get_contracts_with_repayments_in_last_90_days()
        active_contracts_count = active_contracts.count()
        repayments = self.get_repayments_in_last_90_days()
        repayments = repayments.filter(lambda repayment: repayment.time >= start_date and repayment.time <= end_date)

        if active_contracts_count > 0:
            sum_paid_repayments = orm.sum(repayment.amount_paid for repayment in repayments)
            average = int(float(sum_paid_repayments) / active_contracts_count)
        else:
            average = 0

        return average

    @db_session
    def average_unit_cost(self):
        contract_paid_in_last_90_days = self.get_contracts_with_repayments_in_last_90_days()
        active_contracts_count = contract_paid_in_last_90_days.count()

        sum_cost_of_all_contracts = orm.sum(contract.offer.unit_cost for contract in contract_paid_in_last_90_days if contract.offer.unit_cost)

        if not active_contracts_count or not sum_cost_of_all_contracts:
            return "0.00 "+SettingsService.get_setting('CurrencySymbol')

        avg_cost_of_all_contracts = int(sum_cost_of_all_contracts)/ int(active_contracts_count)

        return "{:,.2f} {}".format(float(avg_cost_of_all_contracts), SettingsService.get_setting('CurrencySymbol'))
