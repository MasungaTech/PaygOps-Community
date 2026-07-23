import string
from flask_login import login_required, current_user
from flask import request, abort, flash, redirect, url_for, render_template
from pony.orm import db_session, commit
from sales_system.lead_generator.services.lead_generator_getter_service import LeadGeneratorGetterService

from shared.helpers.authorizer import authorizer
from sales_system.lead_generator.model import LeadGenerator
from sales_system.lead_generator.services.lead_generator_edit_service import LeadGeneratorEditService
from sales_system.lead_generator.web_app import lead_generator
from sales_system.lead_generator.services.lead_generator_type_service import LeadGeneratorTypeService


@lead_generator.route('/<int:generator_id>/edit', methods=['GET', 'POST'])
@login_required
@authorizer('EditLeadGenerators')
@db_session
def edit_lead_generator(generator_id):
    lg = LeadGeneratorGetterService.get_from_user_and_id(current_user, generator_id, strict=True, main_resource=True)
    return render_template('edit_lead_generator.html',
                           lg_types=LeadGeneratorTypeService.get_list(current_user, exclude_default=True),
                           lead_generator=lg)
