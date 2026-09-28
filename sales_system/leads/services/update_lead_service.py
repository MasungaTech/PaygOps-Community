from sales_system.leads.services.edit_lead_service import EditLeadService
from sales_system.leads.models.lead import Lead
from sales_system.leads.services.lead_getter_service import LeadGetterService

class UpdateLeadService:
    @classmethod
    def update(cls, descriptor, user):
        lead = LeadGetterService.get_from_user_and_id(user, descriptor['id'], strict=True)
        EditLeadService.edit_from_data_and_user(lead, descriptor, user)
