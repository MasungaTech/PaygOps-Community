from flask_login import login_required, current_user
from pony.orm import db_session
from flask import render_template, request
from shared.helpers.authorizer import authorizer
from sales_system.lead_generator.services.lead_generator_sorter_service import LeadGeneratorSorter
from sales_system.lead_generator.services.lead_generator_getter_service import LeadGeneratorGetterService
from shared.helpers.pagination import Pagination
from sales_system.lead_generator.web_app import lead_generator
from sales_system.lead_generator.services.lead_generator_type_service import LeadGeneratorTypeService



@lead_generator.route('/', methods=['GET', 'POST'])
@login_required
@authorizer('ViewLeadGenerators')
@db_session
def list_lead_generator():
    if request.method == 'POST':
        active_filter = request.form.get('active_filter', 'default')
        lead_generator_type = request.form.get('lead_generator_type', None)
    else:
        active_filter = request.args.get('active_filter', 'default')
        lead_generator_type = request.args.get('lead_generator_type', None)
    params = 'active_filter={}'.format(active_filter)
    pagination = Pagination.generate(request, params)
    pagination.sort = request.args.get('sort', 'id:desc')

    lead_generators = LeadGeneratorGetterService.get_list(current_user, search=pagination.search, active_filter=active_filter, lead_generator_type=lead_generator_type)
    pagination.objects = LeadGeneratorSorter.sort(lead_generators, pagination.sort)
    lg_types = LeadGeneratorTypeService.get_list(current_user)

    return render_template('list_lead_generator.html',
                           pagination=pagination,
                           active_filter=active_filter,
                           lead_generator_type=lead_generator_type,
                           lg_types=lg_types)
