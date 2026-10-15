from datetime import datetime, timedelta
from flask import render_template, abort, request
from flask_login import current_user, login_required
from pony.orm import db_session

from sales_system.lead_generator.model import LeadGenerator
from sales_system.lead_generator.services.lead_generator_getter_service import LeadGeneratorGetterService
from sales_system.leads.services.sort_lead_service import LeadSorter
from shared.helpers.authorizer import authorizer
from sales_system.sales_dashboard.views import Stats_Helper
from sales_system.lead_generator.services.other_services import LeadGeneratorPieChartService
from sales_system.lead_generator.web_app import lead_generator
from shared.helpers.pagination import Pagination


@lead_generator.route('/<int:generator_id>', methods=["GET"])
@login_required
@authorizer('ViewLeadGenerators')
@db_session
def view_lead_generator(generator_id):

    lead_generator = LeadGeneratorGetterService.get_from_user_and_id(current_user, generator_id, strict=True, main_resource=True)

    converted_leads_pagination = Pagination.generate(request, tab='converted_leads', default_sort='')
    converted_leads_pagination.objects = LeadSorter.sort(lead_generator.getConvertedLeads(), converted_leads_pagination.sort)
    
    lg_pie_chart_data = LeadGeneratorPieChartService(lead_generator)
    lead_offer_type_data = lg_pie_chart_data.leads_offer_types()
    client_offer_type_data = lg_pie_chart_data.clients_offer_types()

    return render_template(
        'view_lead_generator.html',
        lead_generator=lead_generator,
        BeginDate=datetime.now()-timedelta(days=365),
        EndDate=datetime.today(),
        converted_leads_pagination=converted_leads_pagination,
        lead_offer_type_data=lead_offer_type_data,
        client_offer_type_data=client_offer_type_data
    )
