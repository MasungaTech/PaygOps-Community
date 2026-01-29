from datetime import datetime

from pony.orm import count, db_session, desc, left_join, select

import config
from core_system.client.models import Client
from core_system.person.models.person_model import Person
from sales_system.lead_generator.helpers import (get_current_day_month_year,
                                                 get_previous_month)
from sales_system.leads.models.lead import Lead
from shared.helpers.chart import (ChartService, ChartValues,
                                  DailyGraphPointsService, GroupedLabels,
                                  MonthlyGraphPointsService,
                                  WeeklyGraphPointsService)
from shared.helpers.date_helper import (DateDifferenceService,
                                        get_index_by_date_frequency,
                                        get_last_datetime_of_date_label,
                                        get_time_since_date, interval_dates,
                                        month_date_range)
from shared.helpers.week_helper import WeekService
from shared.services.translation_service import TranslationService


class MonthlyGraphPointsService:
    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date
        self.data = []

    @property
    def total_time(self):
        return DateDifferenceService.monthly_diff(self.end_date, self.start_date) + 1

    @property
    def time_passed(self):
        return DateDifferenceService.monthly_diff(WeekService.get_weekly_date(1), self.end_date)

    def from_date(self, n):
        return DateDifferenceService.get_monthly_date(self.total_time - n + self.time_passed + 1)

    def to_date(self, n):
        return DateDifferenceService.get_monthly_date(self.total_time - 1 - n + self.time_passed + 1)

    def generate_graph_points(self, y_func):
        for n in range(self.total_time):
            x_value = DateDifferenceService.get_monthly_date(self.total_time - n + self.time_passed + 1).strftime(
                "%b %Y")

            y_value = y_func(self.from_date(n), self.to_date(n))

            self.data.append((x_value, y_value))
        return self.data


class WeeklyGraphPointsService:
    def __init__(self, start_date, end_date):
        self.start_date = start_date.date()
        self.end_date = end_date.date()
        self.data = []

    @property
    def total_time(self):
        diff = DateDifferenceService.get_weekly_difference(self.start_date, self.end_date)
        return diff + 1

    @property
    def time_passed(self):
        return DateDifferenceService.get_weekly_difference(WeekService.get_weekly_date(), self.end_date)

    def from_date(self, n):
        return WeekService.get_weekly_date(self.total_time - n + self.time_passed + 1)

    def to_date(self, n):
        return WeekService.get_weekly_date(self.total_time - 1 - n + self.time_passed + 1)

    def generate_graph_points(self, y_func):
        for n in range(self.total_time):
            x_value = WeekService.get_weekly_date(self.total_time - n + self.time_passed + 1).strftime(
                "%d %b %Y")
            y_value = y_func(self.from_date(n), self.to_date(n))

            self.data.append((x_value, y_value))
        return self.data


class BaseDataService:
    def __init__(self, lead_generator, start_date=None,
                 end_date=datetime.now().replace(microsecond=0, second=0),
                 frequency='m'):

        self.lead_generator = lead_generator
        self.start_date = start_date
        self.end_date = end_date
        self.frequency = frequency  # d:daily, w:weekly, m:monthly
        self._set_start_date()

    def _set_start_date(self):
        if not self.start_date:
            lg_src_lead = LeadGeneratorLeadService(self.lead_generator)
            first_lead = lg_src_lead.get_first_lead_by_reception_date()

            if first_lead:
                self.start_date = first_lead.receptionTime
                self.start_date = self.start_date.replace(microsecond=0, second=0)

    @property
    def data_point_service(self):
        if self.frequency == 'm':
            return MonthlyGraphPointsService(self.start_date, self.end_date)
        elif self.frequency == 'w':
            return WeeklyGraphPointsService(self.start_date, self.end_date)
        elif self.frequency == 'd':
            return DailyGraphPointsService(self.start_date, self.end_date)


class LeadGeneratorLineChartService:
    def __init__(self, lead_generator):
        self.lead_generator = lead_generator

    def new_leads_info(self, lead_generator, start_date, end_date, frequency):
        info = self.generate_leads_data(lead_generator,
                                        start_date,
                                        end_date,
                                        frequency=frequency)
        return ChartService.generate_response(info)

    def new_leads_by_offer_type_info(self, lead_generator, start_date, end_date, frequency):
        info = self.generate_leads_data_with_fn(lead_generator,
                                        start_date,
                                        end_date,
                                        lambda l: config.OFFERS_HUMAN_READABLE_TYPES_SHORT[getattr(l.offer,'type', None)],
                                        frequency=frequency)
        return ChartService.generate_response(info)

    def drop_rate_info(self, lead_generator, start_date, end_date, frequency):
        info = self.generate_client_drop_rate_data(lead_generator,
                                                   start_date,
                                                   end_date,
                                                   frequency=frequency)

        return ChartService.generate_response(info)

    def generate_leads_data(self,
                            lead_generator,
                            start_date,
                            end_date,
                            frequency='m'):
        labels = interval_dates(start_date, end_date, frequency)
        leads = lead_generator.leads_by_date(start_date, end_date)

        group = GroupedLabels(labels)

        for lead in leads:
            index = get_index_by_date_frequency(lead.statusUpdate,
                                                frequency=frequency)
            key = lead.status.name
            group.append(TranslationService.ftext('New Leads'), index)
            group.append(key, index)
        return group

    def generate_leads_data_with_fn(self,
                                    lead_generator,
                                    start_date,
                                    end_date,
                                    get_key_fn,
                                    frequency='m'):

        labels = interval_dates(start_date, end_date, frequency)
        leads = lead_generator.leads_by_date(start_date, end_date)
        group = GroupedLabels(labels)

        for lead in leads:
            index = get_index_by_date_frequency(lead.statusUpdate,
                                                frequency=frequency)
            key = get_key_fn(lead)
            group.append(key, index)
        return group

    def generate_devices_data(self,
                              lead_generator,
                              start_date,
                              end_date,
                              get_key_fn=lambda d: d.device.payment_type(),
                              frequency='m'):

        labels = interval_dates(start_date, end_date, frequency)
        leads = lead_generator.leads_by_date(start_date, end_date)
        group = GroupedLabels(labels)

        for lead in leads:
            device = lead.get_first_device()

            if device is None:
                continue

            index = get_index_by_date_frequency(lead.statusUpdate,
                                                frequency=frequency)

            key = get_key_fn(device)
            group.append(key, index)
        return group

    def generate_client_drop_rate_data(self,
                                       lead_generator,
                                       start_date,
                                       end_date,
                                       frequency='m'
                                       ):
        labels = interval_dates(start_date, end_date, frequency)
        lg_client_srv = LeadGeneratorClientService(lead_generator)
        group = ChartValues(labels)

        for label in labels:
            d = get_last_datetime_of_date_label(label, frequency)
            rate = lg_client_srv.cumulative_drop_rate(d)

            group.fix_values(label, rate)

        return group


class LeadGeneratorLeadsDataService(BaseDataService):

    def lead_acquisition_trend_data(self):
        if not self.start_date:
            return {}

        if isinstance(self.start_date, datetime):
            self.start_date = self.start_date

        lg_lead_srvc = LeadGeneratorLeadService(self.lead_generator)
        data_service = self.data_point_service
        return data_service.generate_graph_points(lg_lead_srvc.count_leads_from)


class LeadGeneratorPieChartService:
    def __init__(self, lead_generator):
        self.lead_generator = lead_generator

    def leads_offer_types(self):
        leads = self.lead_generator.leads if self.lead_generator else Lead.select()
        offers_count = select((o.type, count()) for l in leads for o in l.offer)[:]
        return sorted((config.OFFERS_HUMAN_READABLE_TYPES_SHORT[o[0]], o[1]) for o in offers_count)


    def clients_offer_types(self):
        leads = self.lead_generator.getConvertedLeads()
        offers_count = select((o.type, count()) for l in leads for o in l.offer)[:]
        return sorted((config.OFFERS_HUMAN_READABLE_TYPES_SHORT[o[0]], o[1]) for o in offers_count)


class LeadGeneratorLeadService:
    def __init__(self, lead_generator):
        self.lead_generator = lead_generator

    @db_session
    def get_leads(self):
        return self.lead_generator.leads

    @db_session
    def get_lead_count(self):
        return self.lead_generator.leads.count()

    @db_session
    def get_first_lead_by_reception_date(self):
        return self.get_leads().order_by(desc(lambda l: l.receptionTime)).first()

    @db_session
    def get_first_lead_by_entry_date(self):
        return self.get_leads().filter(lambda l: l.entryDate is not None).order_by(desc(lambda l: l.entryDate)).first()

    def get_last_lead_by_entry_date(self):
        return self.get_leads().filter(lambda l: l.entryDate is not None).order_by((lambda l: l.entryDate)).first()

    @db_session
    def count_leads_from(self, since_date, to_date):
        return self.get_leads().filter(lambda l: since_date < l.receptionTime
                                       and l.receptionTime <= to_date).count()


class LeadGeneratorBaseClass:
    def get_first_lead(self):
        """
        Number of months since Lead Generator created its first lead
        :return: integer
        """
        lead_gen_lead_service = LeadGeneratorLeadService(self)
        first_lead = lead_gen_lead_service.get_first_lead_by_entry_date()
        if first_lead:
            return get_time_since_date(date=first_lead.entryDate.date(), months=True)

        return 0

    def get_installed_leads_last_month(self):
        """
        Number of leads installed last month from current date
        :return: integer
        """
        day, month, year = get_current_day_month_year()
        month, year = get_previous_month(month, year)
        installed_leads_last_month = self.installed_in_month(month, year)
        return installed_leads_last_month

    def last_quarter_installed_leads(self):
        """
        Average of installed leads in the past 3 months
        :return: float (1 decimal)
        """
        day, month, year = get_current_day_month_year()
        installed_past_3_months = list()
        for n in range(1, 4):
            month, year = get_previous_month(month, year)
            installed_past_3_months.extend(self.installed_in_month(month, year))
        return installed_past_3_months

    def last_quarter_average(self):
        return round(len(self.last_quarter_installed_leads()) / 3, 1)

    def month_average(self):
        """
        Average of all installed leads per month since the beginning
        :return: float (1 decimal)
        """
        total_months = self.get_first_lead()
        return round(self.getConvertedLeadsCount() / total_months, 1) if total_months > 0 else 0

    def drop_rate(self):
        """
        Calculate amount of installed leads that were uninstalled/total installed leads
        :return: float (1 decimal)
        """
        installed = len(self.getConvertedLeads())
        return round(self.getFailedClientsCount() / installed * 100, 2) if installed > 0 else 0

    def installed_in_month(self, month, year):
        """
        Number of leads installed in a given month/year
        :param month: int [1-12]
        :param year: int
        :return: [Lead] (List of Lead objects)
        """
        installed = self.getConvertedLeads()
        since_date, to_date = month_date_range(month, year)
        return installed.filter(lambda lead: lead.statusUpdate >= since_date and lead.statusUpdate < to_date)


class LeadGeneratorClientService:

    def __init__(self, lead_generator):
        self.lead_generator = lead_generator

    @db_session
    def first_client_installed(self):
        all_clients = sorted(self.get_all_clients(),
                             key=lambda l: l.RegistrationDate)

        if len(all_clients) > 0:
            return all_clients[0]

        return None

    @db_session
    def first_client_installed_date(self):
        return self.first_client_installed().RegistrationDate if self.first_client_installed() else None
    
    @db_session
    def get_all_clients(self):
        return [e.person.client for e in self.lead_generator.leads if e.person.client]

    @db_session
    def current_clients_between(self, start, until):
        clients = self.get_all_clients()
        return [c for c in clients
                if c.RegistrationDate >= start
                and (c.active or c.termination_date <= until)]

    @db_session
    def dropped_clients_between(self, start, until):
        persons = select(person for person in Person
                         for lead in person.lead if lead.generator == self.lead_generator)
        clients_from_generator = select(c for c in Client if c.person in persons)
        return left_join(c for c in clients_from_generator
                         if c.termination_date >= start and c.termination_date <= until)

    def drop_rate_between(self, start, end):
        drop_sum = len(self.dropped_clients_between(start, end))
        client_sum = len(self.current_clients_between(start, end))
        return self.calculate_rate(drop_sum, client_sum)

    def cumulative_drop_rate(self, end):
        start = self.first_client_installed_date() if self.first_client_installed_date() else datetime.now()
        drop_sum = len(self.dropped_clients_between(start, end))
        client_sum = len(self.current_clients_between(start, end))
        return self.calculate_rate(drop_sum, client_sum)

    def calculate_rate(self, numerator, denominator):
        try:
            rate = numerator / denominator
        except ZeroDivisionError:
            return 0
        else:
            return round(rate, 2)

    @staticmethod
    def registration_date_sort(e):
        return e.RegistrationDate
