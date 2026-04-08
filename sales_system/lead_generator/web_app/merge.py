from core_system.users.services.user_getter_service import UserGetterService
from flask_login import login_required, current_user
from pony import orm

from sales_system.lead_generator.services.lead_generator_getter_service import LeadGeneratorGetterService
from shared.helpers.authorizer import authorizer
from sales_system.lead_generator.web_app import lead_generator
from shared.helpers.select2 import render


@lead_generator.route('/<int:generator_id>/merge_with_user', methods=["GET"])
@login_required
@authorizer('MergeLeadGenerators')
@orm.db_session
def merge_lead_generator_with_user(generator_id):
    lead_generator = LeadGeneratorGetterService.get_from_user_and_id(current_user, generator_id, strict=True, main_resource=True)
    all_users = UserGetterService.get_list(current_user.reload())

    select2 = {
        'users': {
            'items': all_users,
            'text': 'full_name',
            'person_search_field': True
        }
    }
    return render('merge_lead_generator.html',
                    select2=select2,
                    lead_generator=lead_generator)
