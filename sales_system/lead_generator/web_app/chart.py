from flask_login import current_user, login_required
from flask import request, abort
from pony.orm import db_session
from sales_system.lead_generator.services.lead_generator_getter_service import LeadGeneratorGetterService

from shared.helpers.authorizer import authorizer
from sales_system.lead_generator.model import LeadGenerator
from sales_system.lead_generator.services.other_services import LeadGeneratorLineChartService
from shared.helpers.date_helper import from_str_to_date
from ..helpers import set_date_from_str
from sales_system.lead_generator.web_app import lead_generator


@lead_generator.route('/chart/<string:chart_type>/<int:generator_id>', methods=['GET'])
@login_required
@authorizer('ViewLeadGenerators')
@db_session
def view_lead_generator_chart(chart_type, generator_id):
    lead_generator = LeadGeneratorGetterService.get_from_user_and_id(current_user, generator_id, strict=True, main_resource=True)
    chart = LeadGeneratorLineChartService(lead_generator)
    format = request.values.get('format', '%Y-%m-%d')
    frequency = request.values.get('frequency', 'm')
    start_date = from_str_to_date(request.values.get('start_date'), format=format)
    end_date = from_str_to_date(request.values.get('end_date'), format=format)
    if chart_type == 'new_leads':
        return chart.new_leads_info(lead_generator,
                                    start_date,
                                    end_date,
                                    frequency=frequency)
    if chart_type == 'new_leads_by_offer_type':
        return chart.new_leads_by_offer_type_info(lead_generator,
                                    start_date,
                                    end_date,
                                    frequency=frequency)
    if chart_type == 'drop_rate':
        return chart.drop_rate_info(lead_generator,
                                    start_date,
                                    end_date,
                                    frequency=frequency)