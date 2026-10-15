from pony import orm
from core_system.core_entities import db


class LeadFinderService:

    @staticmethod
    def find_lead_matching_payment_account(paying_account, person=None):
        paying_account_name = paying_account.FullName
        lead_matching = orm.select(lead for lead in db.Lead if lead.future_contract_reference == paying_account_name
                               and lead.awaiting_payment).first()
        if lead_matching:
            return lead_matching

        if person:
            return LeadFinderService.find_leads_awaiting_payment_matching_person(person)
        else:
            return None

    @staticmethod
    def find_leads_awaiting_payment_matching_person(person):
        # Find lead with Awaiting Payment status (#3)
        if person is not None and person.lead:
            for lead in person.lead:
                if lead.awaiting_payment:
                    return lead
        return None
