from flask import flash, url_for, request
from flask_login import login_required, current_user
from pony.orm import db_session
from sales_system.leads.models.lead_status import LeadStatus
from sales_system.leads.models.status_category import StatusCategory
from sales_system.leads.services.lead_status_change_service import LeadStatusChangeService
from shared.helpers.select2 import render
from shared.helpers.authorizer import authorizer
from . import transaction_request
from payg_loan_system.devices.device_list_service import DeviceListService

from sales_system.leads.services.lead_getter_service import LeadGetterService
from payg_loan_system.transaction_requests.nonpayg_device_picker import (
    should_force_auto_generated_nonpayg,
    should_show_auto_generated_nonpayg,
)


@transaction_request.route('/registration/content/', methods=['GET'])
@transaction_request.route('/registration/content/<int:lead_id>', methods=['GET'])
@login_required
@authorizer('RegisterActions')
@db_session
def registration_transaction_content(lead_id=None):

    this_lead = LeadGetterService.get_from_user_and_id(current_user, lead_id, strict=True, main_resource=True)
    offer = this_lead.offer if this_lead else None
    allowed_dest_categories = [s.category for s in LeadStatusChangeService.get_allowed_statuses_from_lead(this_lead, current_user)]
    can_transition_to_installed = StatusCategory.installed in allowed_dest_categories

    not_used_devices = DeviceListService.get_non_used_devices_for_user_list(current_user, offer)
    select2 = {
        'all_devices': {
            'items': not_used_devices,
            'id': 'composed_serial',
            'text': 'composed_serial',
            'data': {
                'apitype': 'api_type'
            },
            'url': url_for(
                'transaction_request.registration_transaction_content',
                lead_id=lead_id
            ),
            'raw_format': True,
            'force_ajax': True
        }
    }

    show_nonpayg = should_show_auto_generated_nonpayg(offer)
    force_nonpayg = should_force_auto_generated_nonpayg(offer)

    return render(
        'registration_transaction_content.html',
        this_lead=this_lead,
        select2=select2,
        show_nonpayg=show_nonpayg,
        force_nonpayg=force_nonpayg,
        can_transition_to_installed=can_transition_to_installed
    )
