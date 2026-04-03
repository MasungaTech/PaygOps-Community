import calendar
from datetime import datetime, timedelta
from config import ENV_VAR
from payg_loan_system.contracts.models.addons_model import ContractAddOn
from payg_loan_system.contracts.models.repayment_model import ContractRepayment

from pony.orm import *
from pony import orm

from payg_loan_system.payments.models.payment import Payment
from payg_loan_system.payments.models.wallet import PaymentWalletType
from sales_system.lead_generator.model import LeadGenerator
from core_system.client.models import Client
from core_system.core_entities import db
from shared.helpers.time_helpers import getMonthDate, getWeekDate
from sales_system.leads.models.lead import Lead
from shared.services.money import MoneyFormatter


class StatsEngine:

    @db_session
    def TimeBetweenLeadAndRegistration(self, SinceDate=None, ToDate=None):
        if SinceDate is None:
            SinceDate = datetime.today()-timedelta(days=30)
        if ToDate is None:
            ToDate = datetime.today()
        contracts = orm.select(contract for contract in db.Contract if contract.start_time >= SinceDate and contract.start_time < ToDate)
        leads = orm.select(lead for lead in Lead if lead.contract in contracts)
        lead_dates = orm.select(lead.entryDate for lead in leads)
        if ENV_VAR == 'TEST': lead_dates = [d for d in lead_dates if d]
        average_lead_generation = avg([datetime.timestamp(lead_date) for lead_date in lead_dates])
        client_dates = orm.select(contract.start_time for contract in contracts)
        average_registration = avg([datetime.timestamp(client_date) for client_date in client_dates])
        if client_dates and average_registration:
            return (average_registration-average_lead_generation)/(3600*24)
        else:
            return 0

    @db_session
    def GetSubNumberPerLeadGenerator(self, SinceDate=None, ToDate=None, Limit=None):
        data = {}
        if ToDate is None :
            ToDate = datetime.today()
        clients = select(E for E in Client if E.person.lead)
        if SinceDate is not None:
            clients = clients.filter(lambda E: E.RegistrationDate > SinceDate and E.RegistrationDate < ToDate)
        leads = orm.select(lead for lead in Lead if lead.person.client in clients)
        lead_generators = select(lg for lg in LeadGenerator)
        for lg in lead_generators:
            data[f'{lg.person.name} {lg.person.surname} ({lg.id})'] = leads.filter(lambda lead: lead.generator == lg).count()
        if Limit is not None:
            data = sorted(data.items(), key=lambda x: x[1], reverse=True)[:Limit]
        else:
            data = sorted(data.items(), key=lambda x: x[1], reverse=True)
        return data

    @db_session
    def GetLeadConversionRate(self):
        Leads = Lead.select()
        AllLeads = Leads.count()
        if AllLeads != 0:
            ConvertedLeads = orm.select(lead for lead in Leads if lead.installed).count()
            Rate = round(ConvertedLeads/AllLeads, 3)
            return int(Rate*1000)/10
        else:
            return 0

    @db_session
    def GetLeadsNumber(self, SinceDate=None, ToDate=None):
        if ToDate is None :
            ToDate = datetime.today()
        if SinceDate is None:
            SinceDate = datetime(1980,1,1)
        LeadsNumber=select(L for L in Lead if (L.receptionTime >= SinceDate) and (L.receptionTime < ToDate)).count()
        return LeadsNumber

    @db_session
    def GetLeadsNumberPerLeadGenerator(self, SinceDate=None, ToDate=None, Limit=None):
        data = {}
        if ToDate is None:
            ToDate = datetime.today()
        leads = orm.select(lead for lead in Lead)
        if SinceDate is not None:
            leads = leads.filter(lambda L: (L.receptionTime >= SinceDate) and (L.receptionTime < ToDate))
        lead_generators = select(lg for lg in LeadGenerator)
        for lg in lead_generators:
            data[f'{lg.person.name} {lg.person.surname} ({lg.id})'] = leads.filter(lambda lead: lead.generator == lg).count()
        if Limit is not None:
            data = sorted(data.items(), key=lambda x: x[1], reverse=True)[:Limit]
        else:
            data = sorted(data.items(), key=lambda x: x[1], reverse=True)
        return data

    @db_session
    def GetTurnover(self, SinceDate=None, ToDate=None):
        if ToDate is None:
            ToDate = datetime.today()
        if SinceDate is None:
            SinceDate = datetime(1980, 1, 1)
        repayment_turnover = orm.select(repayment.amount_paid for repayment in ContractRepayment
                                     if repayment.time > SinceDate and repayment.time <= ToDate).sum()
        addons_turnover_total = orm.select(addon.total_amount for addon in ContractAddOn
                                        if addon.time_paid > SinceDate and addon.time_paid <= ToDate).sum()
        addons_turnover_discounted = orm.select(addon.discounted_amount for addon in ContractAddOn
                                        if addon.time_paid > SinceDate and addon.time_paid <= ToDate).sum()
        return repayment_turnover + (addons_turnover_total - addons_turnover_discounted)

    @db_session
    def GetAverageTurnover(self, SinceDate=None, ToDate=None):
        if ToDate is None :
            ToDate = datetime.today()
        if SinceDate is None:
            SinceDate = self.GetLastYearDate()
        MonthsNumber = self.GetMonthDifference(ToDate,SinceDate)
        Turnover = self.GetTurnover(SinceDate, ToDate)
        TurnoverTab = []
        if MonthsNumber == 0:
            AverageTurnover=Turnover
            TurnoverTab.append(0)
        else :
            AverageTurnover = round(Turnover/MonthsNumber)
            TurnoverTab.append(Turnover)
        dict = {"Turnover":Turnover,"TurnoverTab":TurnoverTab,"AverageTurnover":AverageTurnover}
        return dict

    @db_session
    def GetNumberOfPayments(self, SinceDate=None, ToDate=None):
        if ToDate is None:
            ToDate = datetime.today()
        if SinceDate is None:
            SinceDate = datetime(1980, 1, 1)
        number_of_payments = select(p for p in Payment if (p.PaymentReceptionTime >= SinceDate)
                                    and (p.PaymentReceptionTime < ToDate)
                                    and (p.PaymentWallet.Type == PaymentWalletType.cash or p.PaymentWallet.Type == PaymentWalletType.mobile_money)
                                    and p.reversed_payment is None
                                    and p.PaymentWallet.client in Client.all()).count()
        return number_of_payments

    @db_session
    def GetWeeklyNumberOfSubscriptions(self, WeeksBefore=0):
        LastWeek=self.GetWeekDate(WeeksBefore+1)
        CurrentWeek=self.GetWeekDate(WeeksBefore)
        SubscriptionThisWeek=select(E for E in Client if (E.RegistrationDate > LastWeek) and (E.RegistrationDate < CurrentWeek))
        return SubscriptionThisWeek.count()


#---------- Revenue --------------------

    @db_session
    def GetAverageRevenuePerCustomer(self, SinceDate, ToDate=None):
        if ToDate is None:
            ToDate = datetime.today()
        ActiveCustomers = select(E for E in Client if (E.RegistrationDate < SinceDate) and (E.active or E.termination_date > ToDate))
        NumberOfCustomers = ActiveCustomers.count()
        Revenue = self.GetTurnover(SinceDate, ToDate)
        if NumberOfCustomers == 0:
            AvgRevenue = 0
        else:
            AvgRevenue = round(Revenue / NumberOfCustomers, 3)
        return int(AvgRevenue*10)/10

    @db_session
    def GetMonthlyRevenueChange(self, MonthsBefore=0):
        ThisMonthStart = self.GetMonthDate(MonthsBefore)
        ThisMonthEnd = self.GetMonthDate(MonthsBefore-1)
        PrevMonthStart = self.GetMonthDate(MonthsBefore+1)
        ThisRevenue = self.GetTurnover(ThisMonthStart,ThisMonthEnd)
        PrevRevenue = self.GetTurnover(PrevMonthStart,ThisMonthStart)
        if PrevRevenue == 0:
            RevenueChange = 0
        else:
            RevenueChange = round((ThisRevenue - PrevRevenue)/PrevRevenue, 3)
        return int(RevenueChange*1000)/10

#---------- Global Stats ---------------

    def GetAccountReceivable(self):
        Clients = select(E for E in Client if E.active)
        return select(c.cached_total_value for c in db.Contract if c.client in Clients).sum()

    def GetActiveClientsRegisteredDuringPeriod(self, sinceDate, toDate):
        return select(E for E in Client if E.active
                      and sinceDate < E.RegistrationDate and E.RegistrationDate <= toDate)

    def GetAccountReceivableDuringPeriod(self, sinceDate, toDate):
        Clients = self.GetActiveClientsRegisteredDuringPeriod(sinceDate, toDate)
        return select(c.cached_total_value for c in db.Contract if c.client in Clients).sum()

    def GetExpensesDuringPeriod(self, sinceDate, toDate):
        from accounting_system.accounting_db import Expense
        return sum(E.amount for E in Expense if sinceDate < E.entryDate and E.entryDate <= toDate)

    def GetShareOfPettyCashDuringPeriod(self, sinceDate, toDate):
        from accounting_system.accounting_db import Expense
        expenseInPeriod = select(E for E in Expense if sinceDate < E.entryDate and E.entryDate <= toDate)
        pettyCashExpenses = expenseInPeriod.filter(lambda E: E.receiptType == 2)
        expenseCount = count(expenseInPeriod)
        if expenseCount == 0:
            return 0
        else:
            return count(pettyCashExpenses)/expenseCount

    def GetNumberOfClients(self):
        NumberOfClients = count(E for E in Client if E.active)
        return NumberOfClients

#---------- Helper Methods -------------

    def GetWeekDate(self, WeeksBefore=0):
        return getWeekDate(WeeksBefore+1)

    def GetMonthDate(self, MonthsBefore=0):
        return getMonthDate(MonthsBefore+1)

    def GetMonthDifference(self, Date1, Date2):
        return (Date1.year - Date2.year)*12 + Date1.month - Date2.month

    def GetWeekDifference(self, Date1, Date2):
        monday1 = (Date1 - timedelta(days=Date1.weekday()))
        monday2 = (Date2 - timedelta(days=Date2.weekday()))
        diff = int((monday2 - monday1).days / 7)
        return diff

    def AddMonths(self, Date, Months):
        month = Date.month - 1 + Months
        year = int(Date.year + month / 12)
        month = month % 12 + 1
        day = min(Date.day,calendar.monthrange(year,month)[1])
        return datetime(year,month,day)

    def GetAverageDate(self):
        return datetime.now() - timedelta(days=365)

    def GetLastYearDate(self):
        return datetime.now()-timedelta(days=365)

    @db_session
    def generate_account_data(self, start_date, end_date):
        average_turnover = self.GetAverageTurnover(start_date, end_date)
        number_of_clients = self.GetNumberOfClients()
        account_receivable = self.GetAccountReceivable()
        if number_of_clients != 0:
            receivable_per_client = int(account_receivable/number_of_clients * 10)/10
        else:
            receivable_per_client = 0

        return {
            'total_turnover': MoneyFormatter.format(average_turnover['Turnover']),
            'average_turnover': MoneyFormatter.format(average_turnover['AverageTurnover']),
            'number_of_payments': self.GetNumberOfPayments(start_date, end_date),
            'account_receivable': MoneyFormatter.format(account_receivable),
            'average_account_receivable_per_client': MoneyFormatter.format(receivable_per_client)
        }
