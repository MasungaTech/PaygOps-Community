from core_system.client.services.client_tag_getter import ClientTagService
import json
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from payg_loan_system.contracts.models.contract_status import ContractStatus
import random

from flask_login import login_required, current_user
from flask import request, render_template, make_response
from pony.orm import db_session, select

from payg_loan_system.offers.models import OfferType
from core_system.client.services.client_list_service import ClientListService
from sales_system.leads.models.lead_status import LeadStatus
from sales_system.leads.models.status_category import StatusCategory
from sales_system.leads.services.lead_getter_service import LeadGetterService
from messages_system.services.communications_service import CommunicationsService
from messages_system.models.communications import CommunicationCampaign

from shared.logger.loggers import Error
from shared.helpers.authorizer import authorizer
from shared.helpers.clock import Clock
from shared.helpers.form_helpers import dateTimePickerToStandard
from shared.services.celery_queue_service import CeleryQueueService
from shared.services.settings_service import SettingsService

from worker_app.tasks.send_communication_campaign import send_communication_campaign
from shared.helpers.pagination import Pagination


from . import administration

@administration.route('/communication_campaigns', methods=["GET", "POST"])
@login_required
@authorizer('AddOutgoingMessages')
@db_session
def communication_campaigns():

    search = request.form.get('search', '')
    user = request.form.get('user')
    min_date = Clock.localize_to_utc(dateTimePickerToStandard(request.form.get('min_date', '')))
    max_date = Clock.localize_to_utc(dateTimePickerToStandard(request.form.get('max_date', '')))

    campaigns = CommunicationCampaign.select()

    users = select((c.user.id, c.user.full_name) for c in CommunicationCampaign if c in campaigns)

    campaigns = campaigns.filter(lambda c: search.lower() in c.name.lower() or
                                 search.lower() in c.content.lower())
    pagination = Pagination.generate(request, default_sort='id:desc')
    pagination.objects = campaigns


    try:
        user_id = int(user)
    except (TypeError, ValueError):
        user_id = None
    else:
        campaigns = campaigns.filter(lambda c: c.user.id == user_id)

    if min_date:
        campaigns = campaigns.filter(lambda c: c.time.date() >= min_date)

    if max_date:
        campaigns = campaigns.filter(lambda c: c.time.date() <= max_date)

    return render_template(
        'communication_campaigns.html',
        campaigns=campaigns,
        search=search,
        user_id=user_id,
        users=users,
        min_date=min_date,
        max_date=max_date,
        pagination=pagination
    )


@administration.route('/phone_list_example.csv', methods=["GET"])
@login_required
@authorizer('AddOutgoingMessages')
@db_session
def phones_csv_example():
    p = lambda l: str(random.randint(int('1'+'0'*(l-1)), int('9'*l)))
    e1 = '00'+SettingsService.get_setting('PhoneExtension')
    e2 = '+'+SettingsService.get_setting('PhoneExtension')
    minl = SettingsService.get_setting('PhoneLengthMin')
    if minl <= 0:
        minl = 1
    maxl = SettingsService.get_setting('PhoneLength')
    content = ('Telephones\n'+
               '"'+e1+p(minl)+'"\n'+
               e2+p(minl)+'\n'+
               e1+p(maxl)+'\n'+
               e2+p(maxl))
    response = make_response(content)
    content_disp = 'attachment; filename=phone_list_example.csv'
    response.headers["Content-Disposition"] = content_disp
    response.headers["Content-type"] = "text/csv"
    return response


@administration.route('/communication_campaigns/add', methods=["GET", "POST"])
@login_required
@authorizer('AddOutgoingMessages')
@db_session
def communication_tool():

    if request.method == 'POST':

        count = {}

        if 'csv_file' in request.files:

            try:
                rows, valid_phones = CommunicationsService.get_phones(request.files['csv_file'])
            except Error as error:
                return json.dumps({"error": str(error)}), 400

            count['phones'] = {'total': len(rows), 'valid': len(valid_phones), 'invalid': len(rows)-len(valid_phones)}

        if 'recipients_filter' in request.form:

            filters = json.loads(request.form["recipients_filter"])
            client_filter = filters.get("Client", {})
            lead_filter = filters.get("Lead", {})

            clients = ClientListService.filter_for_user(client_filter, current_user)
            leads = LeadGetterService.get_lead_for_communication_tool(lead_filter, current_user)

            count['leads'] = leads.count()
            count['clients'] = clients.count()

        if request.form.get('content') and request.form.get('name') and (clients or leads or valid_phones):
            CeleryQueueService.execute_task(send_communication_campaign, 
                valid_phones,
                [l.id for l in leads],
                [c.id for c in clients],
                request.form.get('content'),
                current_user.id,
                request.form.get('name'),
                filters
            )
            return json.dumps({'success': True}), 200

        return json.dumps(count), 200

    client_statuses = {'all': 'All'}
    client_statuses.update(ContractStatus.to_dict())

    lead_statuses = {'all': 'All'}
    lead_statuses.update({s.id: s.name for s in LeadStatus.select(lambda s: s.category != StatusCategory.installed)})

    offer_types = {'all': 'All', 'none': 'No offer'}
    offer_types.update({t:t for t in OfferType.to_list()})

    client_offer_types = {'all': 'All'}
    client_offer_types.update({t:t for t in OfferType.to_list()})

    locations = [('all', 'All')]
    locations += [(e.id, e.name) for e in OperationalEntitiesGetterService.get_list(current_user, level=2)]

    client_tags = [('all', 'All')]
    client_tags += select((tag.id, tag.name) for tag in ClientTagService.get_list(current_user))[:]

    return render_template(
        'communication_tool.html',
        client_statuses=client_statuses,
        lead_statuses=lead_statuses,
        offer_types=offer_types,
        client_offer_types=client_offer_types,
        locations=locations,
        client_tags=client_tags
    )
