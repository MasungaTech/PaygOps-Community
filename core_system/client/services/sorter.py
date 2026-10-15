from datetime import datetime
from shared.services.sorter import Sorter
from core_system.client.models import Client
from pony import orm


class ClientSorter(Sorter):

    @staticmethod
    def sort_by(field_name):
        options = {
            'id': ClientSorter.by_id,
            'name': ClientSorter.by_name,
            'activation': ClientSorter.client_activation,
            'village': ClientSorter.by_village,
            'gps': ClientSorter.by_gps,
            'offer': ClientSorter.by_offer,
            'seniority': ClientSorter.by_seniority,
            'expires_in': ClientSorter.by_expires_in,
            'payment': ClientSorter.by_payment,
            'interaction': ClientSorter.by_interaction,
            'missed_visits': ClientSorter.by_missed_visits,
            'average_monthly_visits': ClientSorter.by_average_monthly_visits,
            'topic': ClientSorter.by_topic,
            'priority': ClientSorter.by_priority,
            'resolution_time': ClientSorter.by_resolution_time,
            'notes': ClientSorter.by_notes,
            'planning': ClientSorter.by_planning,
        }
        return options.get(field_name, ClientSorter.by_name)

    @staticmethod
    def real_field_sort(field_name, desc=False):
        options = {
            'id': Client.id,
            'name': lambda E: E.person.searchable_name,
            'custom_id': lambda E: E.person.custom_id,
            'activation': False,
            'village': lambda E: E.person.village,
            'gps': False,
            'offer': False,
            'seniority': Client.RegistrationDate,
            'expires_in': lambda c: orm.min(con.next_repayment_due_time for con in c.contracts),
            'payment': False,
            'interaction': False,
            'missed_visits': False,
            'average_monthly_visits': False,
            'topic': False,
            'priority': False,
            'resolution_time': False,
            'notes': False,
            'planning': False,
        }
        options_desc = {
            'name': lambda E: orm.desc(E.person.searchable_name),
            'village': lambda E: orm.desc(E.person.village),
            'custom_id': lambda E: orm.desc(E.person.custom_id),
            'expires_in': lambda c: orm.desc(orm.min(con.next_repayment_due_time for con in c.contracts)),
        }
        if desc:
            return options_desc.get(field_name, options.get(field_name, lambda E: E.person.name))
        return options.get(field_name, lambda E: E.person.name)

    @staticmethod
    def client_activation(object):
        return object.get_average_timeliness_ratio() or 0

    @staticmethod
    def by_name(object):
        return object.full_name

    @staticmethod
    def by_village(object):
        return object.person.village

    @staticmethod
    def by_gps(object):
        return object.GPSCoordinates

    @staticmethod
    def by_offer(object):
        return (object.first_active_contract or object.last_contract).offer

    @staticmethod
    def by_seniority(object):
        return object.RegistrationDate

    @staticmethod
    def by_expires_in(object):
        due = object.get_earliest_payment_due()
        if due:
            return due
        return datetime(2100, 1, 1, 1, 1, 1, 0)

    @staticmethod
    def by_payment(object):
        return object.get_average_repayment_progression() or 0

    @staticmethod
    def by_interaction(object):
        if object.get_last_visit_date():
            return object.get_last_visit_date()
        return datetime(2100, 1, 1, 1, 1, 1, 0)

    @staticmethod
    def by_missed_visits(object):
        return object.get_missed_visits_count()

    @staticmethod
    def by_average_monthly_visits(object):
        return object.get_average_monthly_visits()*12

    @staticmethod
    def by_topic(object):
        issue = object.getOpenIssues().first()

        if issue and issue.type:
            return issue.type.name

        return ''

    @staticmethod
    def by_priority(object):
        issue = object.getOpenIssues().first()

        if issue:
            return issue.priority

        return 0

    @staticmethod
    def by_resolution_time(object):
        issue = object.getOpenIssues().first()

        if issue:
            return issue.getResolutionTime()

        return 0

    @staticmethod
    def by_notes(object):
        return object.Assets

    @staticmethod
    def by_planning(object):
        return object.hasPlannedInteraction()
