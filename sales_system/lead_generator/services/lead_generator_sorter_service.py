from pony import orm
from shared.services.sorter import Sorter
from sales_system.lead_generator.model import LeadGenerator
from datetime import datetime
from dateutil.relativedelta import relativedelta


class LeadGeneratorSorter(Sorter):
    def sort_by(field_name):
        options = {
            'name': LeadGeneratorSorter.sortable_by_name,
            'type': LeadGeneratorSorter.sortable_by_type,
            'leads': LeadGeneratorSorter.sortable_by_leads,
            'id': LeadGeneratorSorter.by_id,
            'seniority': LeadGeneratorSorter.sortable_by_seniority,
            'last_month': LeadGeneratorSorter.sortable_by_installed_leads,
            'monthly_avg': LeadGeneratorSorter.sortable_by_month_average,
            'quarter_avg': LeadGeneratorSorter.sortable_by_quarter_average,
            'drop_rate': LeadGeneratorSorter.sortable_by_drop_rate,
            'shop': LeadGeneratorSorter.sortable_by_shop,
            'active': LeadGeneratorSorter.sortable_by_active,
            'list': LeadGeneratorSorter.sortable_by_leads
        }

        return options.get(field_name, LeadGeneratorSorter.sortable_by_name)

    def real_field_sort(field_name, desc=False):
        this_month = datetime.now().replace(day=1)
        last_month = this_month - relativedelta(months=1)
        options = {
            'id': LeadGenerator.id,
            'name': lambda l: l.person.searchable_name,
            'type': LeadGenerator.type,
            'leads': lambda l: orm.count(l.leads),
            'seniority': LeadGenerator.start_date,
            'last_month': lambda lg: orm.count(lg.leads.filter(lambda l: l.installed and l.statusUpdate >= last_month and l.statusUpdate < this_month)),
            'monthly_avg': False,
            'quarter_avg': False,
            'drop_rate': False,
            'shop': False,
            'active': LeadGenerator.working,
            'list': False
        }

        options_desc = {
            'id': lambda l: orm.desc(l.id),
            'name': lambda l: orm.desc(l.person.searchable_name),
            'type': lambda l: orm.desc(l.type),
            'leads': lambda l: orm.desc(orm.count(l.leads)),
            'seniority': lambda l: orm.desc(l.start_date),
            'active': lambda l: orm.desc(l.working),
        }

        if desc:
            return options_desc.get(field_name, options.get(field_name, lambda l: orm.desc(l.person.name)))

        return options.get(field_name, lambda l: l.person.name)

    @staticmethod
    def sortable_by_name(lead_generator):
        return lead_generator.person.full_name

    @staticmethod
    def sortable_by_type(lead_generator):
        return lead_generator.type

    @staticmethod
    def sortable_by_seniority(lead_generator):
        return lead_generator.start_date

    @staticmethod
    def sortable_by_installed_leads(lead_generator):
        return lead_generator.get_installed_leads_last_month().count()

    @staticmethod
    def sortable_by_month_average(lead_generator):
        return lead_generator.month_average()

    @staticmethod
    def sortable_by_quarter_average(lead_generator):
        return lead_generator.last_quarter_average()

    @staticmethod
    def sortable_by_drop_rate(lead_generator):
        return lead_generator.drop_rate()

    @staticmethod
    def sortable_by_leads(lead_generator):
        return orm.count(lead_generator.leads)

    @staticmethod
    def sortable_by_shop(lead_generator):
        return lead_generator.shop_names()

    @staticmethod
    def sortable_by_active(lead_generator):
        return lead_generator.working
