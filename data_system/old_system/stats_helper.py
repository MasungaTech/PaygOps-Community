"""
stats_helper.py: Contains helper methods for the stats dashboard
"""

import datetime

from pony.orm import *
from data_system.old_system.stats import StatsEngine
from core_system.client.models import Client
from sales_system.leads.models.lead import Lead
from sales_system.lead_generator.model import LeadGenerator
from payg_loan_system.offers.models import Offer
from decimal import Decimal
from pony import orm
from payg_loan_system.contracts.services.contract_list_service import ContractListService
from config import OFFERS_HUMAN_READABLE_TYPES

Stats = StatsEngine()

class StatsHelper:

    @staticmethod
    def _month_start(date_obj):
        return datetime.datetime(date_obj.year, date_obj.month, 1)

    def _iterate_month_periods(self, begin_date, end_date):
        normalized_begin = self._month_start(begin_date)
        normalized_end = self._month_start(end_date)

        total_months = Stats.GetMonthDifference(normalized_end, normalized_begin) + 1

        for offset in range(total_months):
            period_start = Stats.AddMonths(normalized_begin, offset)
            period_end = Stats.AddMonths(period_start, 1)
            yield period_start, period_end, period_start.strftime("%b %Y")

    def GetTurnoverChartData(self, BeginDate, EndDate):
        data = []
        for period_start, period_end, label in self._iterate_month_periods(BeginDate, EndDate):
            cur_number = Stats.GetTurnover(period_start, period_end)
            data.append((label, cur_number))
        return data

    def GetAccountReceivableChartData(self, BeginDate, EndDate):
        data = []
        for period_start, period_end, label in self._iterate_month_periods(BeginDate, EndDate):
            cur_number = Stats.GetAccountReceivableDuringPeriod(period_start, period_end)
            data.append((label, cur_number))
        return data

    def GetExpensesChartData(self, BeginDate, EndDate):
        data = []
        for period_start, period_end, label in self._iterate_month_periods(BeginDate, EndDate):
            cur_number = Stats.GetExpensesDuringPeriod(period_start, period_end)
            data.append((label, cur_number))
        return data

    def GetReceiptTypeData(self, BeginDate, EndDate):
        data = []
        for period_start, period_end, label in self._iterate_month_periods(BeginDate, EndDate):
            cur_number = Stats.GetShareOfPettyCashDuringPeriod(period_start, period_end)
            data.append((label, cur_number * 100))
        return data

    def GetIncomeChartData(self, BeginDate, EndDate):
        data = []
        for period_start, period_end, label in self._iterate_month_periods(BeginDate, EndDate):
            cur_revenue = Stats.GetAccountReceivableDuringPeriod(period_start, period_end)
            cur_expense = Stats.GetExpensesDuringPeriod(period_start, period_end)
            data.append((label, cur_revenue - Decimal(cur_expense)))
        return data

    def GetMonthlyRevenueChangeChartData(self, BeginDate, EndDate):
        data = []
        current_month_start = Stats.GetMonthDate(0)
        for period_start, _, label in self._iterate_month_periods(BeginDate, EndDate):
            months_before = Stats.GetMonthDifference(current_month_start, period_start)
            cur_number = Stats.GetMonthlyRevenueChange(months_before)
            data.append((label, cur_number))
        return data

    def GetRevenuePerCustomerChartData(self, BeginDate, EndDate):
        data = []
        for period_start, period_end, label in self._iterate_month_periods(BeginDate, EndDate):
            cur_number = Stats.GetAverageRevenuePerCustomer(period_start, period_end)
            data.append((label, cur_number))
        return data

    def GetNumberOfPaymentsChartData(self, BeginDate, EndDate):
        data = []
        for period_start, period_end, label in self._iterate_month_periods(BeginDate, EndDate):
            cur_number = Stats.GetNumberOfPayments(period_start, period_end)
            data.append((label, cur_number))
        return data


#--------- Business Dashboard ----------

    def GetLeadsAndClientsPerWeekChartData(self, BeginDate, EndDate):
        Y = Stats.GetWeekDifference(BeginDate, EndDate)
        Z = Stats.GetWeekDifference(EndDate, Stats.GetWeekDate(0))
        data = []
        for N in range(Y):
            curNumber1 = Stats.GetLeadsNumber(Stats.GetWeekDate(Y - N + Z), Stats.GetWeekDate(Y - N + Z - 1))
            curNumber2 = Stats.GetWeeklyNumberOfSubscriptions(Y - 1 - N + Z)
            curDate = Stats.GetWeekDate(Y - N + Z).strftime("%d %b %Y")
            data.append((curDate, curNumber1, curNumber2))
        return data

    def GetLeadGeneratedByGeneratorType(self):
        data = {}
        leads = orm.select(lead for lead in Lead)
        lead_generator_types = orm.select(lg.type.name for lg in LeadGenerator)
        for lgt in lead_generator_types:
            data[lgt] = leads.filter(lambda lead: lead.generator.type.name == lgt).count()

        return sorted(data.items())

    #------------ Lead Generator Charts ---------

    def getLeadsOfferTypeChartData(self, LeadGenerator=None):
        data = {}
        if LeadGenerator is not None:
            leads = LeadGenerator.leads
        else:
            leads = Lead.select()

        panel_sizes = orm.select(offer.panel_size_in_w for offer in Offer)
        for panel_size in panel_sizes:
            data[f'{panel_size}W'] = leads.filter(lambda lead: lead.offer.panel_size_in_w == panel_size).count()
        return sorted(data.items(), key=lambda ps: ps[1], reverse=True)

    def getClientsOfferTypeGlobalChartData(self):
        data = {}
        clients = orm.select(client for client in Client)
        contracts = ContractListService.get_from_clients(clients)

        panel_sizes = orm.select(offer.panel_size_in_w for offer in Offer)
        for panel_size in panel_sizes:
            data[f'{panel_size}W'] = contracts.filter(lambda contract: contract.offer.panel_size_in_w == panel_size).count()
        return sorted(data.items(), key=lambda ps: ps[1], reverse=True)

    def getLeadsPerOfferTypeChartData(self):
        data = {}
        leads = orm.select(lead for lead in Lead)
        offers = orm.select(lead.offer for lead in Lead)
        offer_types = orm.select(offer.type for offer in offers)
        for offer_type in offer_types:
            offer_name = OFFERS_HUMAN_READABLE_TYPES.get(offer_type, OFFERS_HUMAN_READABLE_TYPES[None])
            data[offer_name] = leads.filter(lambda lead: lead.offer.type == offer_type).count()
        return sorted(data.items(), key=lambda ps: ps[1], reverse=True)

    def getClientsPerOfferTypeChartData(self):
        data = {}
        clients = orm.select(client for client in Client)
        contracts = ContractListService.get_from_clients(clients)
        offers = orm.select(contract.offer for contract in contracts)
        offer_types = orm.select(offer.type for offer in offers)
        for offer_type in offer_types:
            offer_name = OFFERS_HUMAN_READABLE_TYPES.get(offer_type, OFFERS_HUMAN_READABLE_TYPES[None])
            count = 0
            for client in clients:
                if any(contract.offer.type == offer_type for contract in list(client.contracts)):
                    count += 1
            data[offer_name] = count
        return sorted(data.items(), key=lambda ps: ps[1], reverse=True)
