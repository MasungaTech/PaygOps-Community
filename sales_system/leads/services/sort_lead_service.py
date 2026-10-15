from shared.services.sorter import Sorter
from sales_system.leads.models.lead import Lead
from pony import orm


class LeadSorter(Sorter):
    def sort_by(field_name):
        options = {
            'id': LeadSorter.by_id,
            'name': LeadSorter.by_name,
            'first_interaction': LeadSorter.by_first_interaction,
            'last_contact': LeadSorter.by_last_contact,
            'next_contact': LeadSorter.by_next_contact,
            'requested_offer': LeadSorter.by_requested_offer,
            'approved_since': LeadSorter.by_approval_date,
            'promised_pay': LeadSorter.by_promised_pay,
            'delivery_date': LeadSorter.by_delivery_date,
            'status': LeadSorter.by_status,
            'use': LeadSorter.by_use}

        return options.get(field_name, LeadSorter.by_status)

    def real_field_sort(field_name, desc=False):
        options = {
            'id': Lead.id,
            'name': lambda l: l.person.searchable_name,
            'custom_id': lambda l: l.person.custom_id,
            'first_interaction': Lead.receptionTime,
            'last_contact': Lead.modifiedDate,
            'next_contact': Lead.nextContact,
            'requested_offer': Lead.offer,
            'approved_since': Lead.decisionTime,
            'promised_pay': Lead.promisedToPay,
            'delivery_date': Lead.agreedDeliveryDate,
            'status': False,
            'use': False
        }
        options_desc = {
            'converted_time': lambda l: orm.desc(l.contract.start_time),
            'custom_id': lambda l: orm.desc(l.person.custom_id),
            'name': lambda l: orm.desc(l.person.searchable_name),
        }
        if desc:
            return options_desc.get(field_name, options.get(field_name, False))
        return options.get(field_name, False)

    @staticmethod
    def by_name(object):
        return object.person.full_name

    @staticmethod
    def by_first_interaction(object):
        return object.receptionTime

    @staticmethod
    def by_last_contact(object):
        return object.modifiedDate

    @staticmethod
    def by_next_contact(object):
        return object.nextContact

    @staticmethod
    def by_requested_offer(object):
        return object.requestedOffer

    @staticmethod
    def by_approval_date(object):
        return object.decisionTime

    @staticmethod
    def by_promised_pay(object):
        if object.promisedToPay:
            return object.promisedToPay
        else:
            return '-'
    @staticmethod
    def by_delivery_date(object):
        return object.agreedDeliveryDate

    @staticmethod
    def by_status(object):
        return object.status.id

    @staticmethod
    def by_use(object):
        return '-'
