import config

if config.ENABLE_ENTERPRISE_FEATURES:
    from after_sales_system.issue_system.services.issue_service import IssueService
else:
    IssueService = None
from core_system.client.services.client_tag_getter import ClientTagService
from datetime import datetime
from flask_login import login_required, current_user
from flask import request, render_template, flash, redirect, url_for
from payg_loan_system.contracts.models.contract_status import ContractStatus
from pony.orm import db_session

from shared.helpers.authorizer import authorizer
from core_system.person.services.form_visibility_rule_getter import FormVisibilityRuleGetterService
from core_system.client.services.client_getter_service import ClientGetterService
from core_system.client.services.client_edit_service import ClientEditService
from payg_loan_system.offers.models import OfferType
from shared.logger.loggers import Error
from shared.services.settings_service import SettingsService

from . import client


@client.route('/<int:client_id>', methods=['GET', 'POST'])
@login_required
@authorizer('ViewClients')
@db_session
def view_client(client_id):
    selected_client = ClientGetterService.get_from_user_and_id(current_user, client_id)
    if not selected_client:
        flash('Client does not exist or you do not have the permission to see it. ')
        return redirect(url_for('client.list_client'))

    client_surveys = FormVisibilityRuleGetterService.get_answers_for_client(selected_client)
    extra_surveys = FormVisibilityRuleGetterService.get_not_answered_surveys(client=selected_client)
    required_forms = FormVisibilityRuleGetterService.get_forms(client=selected_client, required=True)

    current_user_role = current_user.can_access('EditClients', person=selected_client.person)
    formattedCustomButtonURL = ''
    formattedCustomButtons = []
    settings = SettingsService.get_setting('customButtonConfiguration')
    if settings:
        for button in settings:
            if button.get('TargetPage') == 'client' and button.get('TargetUrl'):
                button['TargetUrl'] = button['TargetUrl'].format(
                client_id=selected_client.id,
                name=selected_client.full_name,
                custom_id=selected_client.person.custom_id or '',
                user_id=current_user.id,
                user_name=current_user.full_name,
                client_phone_number=selected_client.person.contactPhone.number if selected_client.person.contactPhone else ''
                )
                formattedCustomButtons.append(button)
    open_issues = []
    if config.ENABLE_ENTERPRISE_FEATURES and IssueService:
        open_issues = IssueService.get_list(current_user, client=selected_client, open=True)

    return render_template(
        'view_client.html',
        person=selected_client.person,
        Client=selected_client,
        current_user=current_user,
        MandatorySurveys=client_surveys,
        extra_surveys=extra_surveys,
        required_forms=required_forms,
        current_user_role=current_user_role,
        user_has_permission_to_erase_phones=current_user.reload().can_access('DeletePhoneNumbers', entity=selected_client.person.village),
        existing_tags=ClientTagService.get_list(current_user),
        tags=[t.id for t in selected_client.tags],
        OfferType=OfferType,
        personIDForSurvey=selected_client.id,
        personType='client',
        open_issues=open_issues,
        formattedCustomButtons=formattedCustomButtons,
        ContractStatus=ContractStatus
    )
