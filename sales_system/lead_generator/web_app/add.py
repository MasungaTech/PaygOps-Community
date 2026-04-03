import json
from flask_login import login_required, current_user
from flask import request, render_template
from pony.orm import db_session
from shared.helpers.authorizer import authorizer
from sales_system.lead_generator.web_app import lead_generator
from sales_system.lead_generator.services.lead_generator_type_service import LeadGeneratorTypeService


@lead_generator.route('/add', methods=['GET', 'POST'])
@login_required
@authorizer('AddLeadGenerators', '.list_lead_generator')
@db_session
def add_lead_generator():
    return render_template('edit_lead_generator.html',
                            lg_types=LeadGeneratorTypeService.get_list(current_user, exclude_default=True))
