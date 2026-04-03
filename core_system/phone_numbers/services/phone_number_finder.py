from pony import orm
from sales_system.leads.services.lead_finder_service import LeadFinderService


class PhoneNumberFinder:

    @staticmethod
    @orm.db_session
    def find_person_preferred_number(person):
        if not person:
            return None
        return person.preferred_phone_number()
