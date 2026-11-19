from flask import request
from pony.orm import db_session

from core_system.users.services.current_user_service import get_current_api_user
from sales_system.leads.models.lead_status import LeadStatus
from sales_system.leads.models.status_category import StatusCategory
from sales_system.leads.services.lead_status_service import LeadStatusService
from shared.api_helpers.documented_resource import DocumentedResource
from shared.api_helpers.server_helpers.jwt_and_schema_verification import verify
from shared.logger.loggers import Error


def serialize_lead_statuses(user):
    allowed_ids = {
        status.id for status in LeadStatusService.get_allowed_statuses_for_new_lead(user)
    }
    category_codes = StatusCategory.to_inv_dict()
    category_rank = {
        category: index
        for index, category in enumerate(LeadStatusService.STATUS_CATEGORY_ORDER)
    }
    statuses = sorted(
        LeadStatus.select(),
        key=lambda status: (category_rank.get(status.category, 99), status.order, status.id),
    )
    return [
        {
            'id': status.id,
            'name': status.name,
            'category': category_codes.get(status.category, status.category),
            'order': status.order,
            'color': status.color,
            'allowed_for_new_lead': status.id in allowed_ids,
        }
        for status in statuses
    ]


class LeadStatusesResource(DocumentedResource):
    """List and replace lead statuses. Not public: a partial POST deletes omitted rows."""

    PUBLIC = False

    @verify(permissions=['ViewLeads', 'AddLeads'])
    @db_session
    def get(self):
        return serialize_lead_statuses(get_current_api_user())

    @verify(permissions=['CustomizePlatformAdmin'])
    @db_session
    def post(self):
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise Error('A lead status update is a map of category codes to status lists.')
        LeadStatusService.edit_statuses(data)
        return serialize_lead_statuses(get_current_api_user())
