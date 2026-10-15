from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual
from sales_system.leads.models.lead import Lead
from sales_system.leads.services.edit_lead_service import EditLeadService
from sales_system.leads.services.lead_getter_service import LeadGetterService


class IndividualLeadResource(BaseAPIResourceIndividual):

    GET_SERVICE = LeadGetterService
    EDIT_SERVICE = EditLeadService
    GET_PERMISSION = 'ViewLeads'
    EDIT_PERMISSION = 'EditLeads'
    OBJECT_NAME = 'Lead'
    MODEL = Lead
    TAG = 'Leads'

    ALLOWED_API_CALLER = ['post']

    SUBACTIONS = {
        'post': {
            'edit_lead_portfolio': {
                'name': "Edit Lead Portfolio",
                'description': "Provide a list of lead IDs and their respective portfolios to be assigned",
                'permissions': ['EditLeads'],
                'properties': ['id', 'portfolio']
            },
        }
    }

    @classmethod
    def _get_relevant_person(cls, this_object):
        return this_object.person
