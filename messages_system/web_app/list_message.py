from flask_login import login_required, current_user
from flask import redirect, request, url_for, flash, render_template
from pony.orm import db_session
from core_system.client.services.client_getter_service import ClientGetterService
from sales_system.leads.services.lead_getter_service import LeadGetterService
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from core_system.users.services.user_getter_service import UserGetterService
from datetime import datetime, timedelta
from shared.helpers.form_helpers import isoDateTimeToUTC, naiveDateTimeToStandard

from shared.helpers.authorizer import authorizer
from shared.helpers.pagination import Pagination

from messages_system.web_app.services import MessageGetterService
from constants import SMS_STATUS_MAP, SMS_STATUS_MAP_SHORT, MESSAGE_RECEIVERS, SENDER_USER_TYPES

from . import message
from shared.helpers.select2 import render


@message.route('/', methods=['GET'])
@login_required
@authorizer('ViewMessages')
@db_session
def list_message(client_id=None, user_id=None, shop_id=None):
    default_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    scope_filter = request.args.get('scope_filter', 'all')
    inout_filter = request.args.get('inout_filter', 'out')
    status_filter = request.args.get('status_filter', '')
    sender_type = request.args.get("sender_type")
    sender_user = UserGetterService.extract_from_user_and_id(current_user, request.args, 'sender_user_id', strict=False)
    user = UserGetterService.extract_from_user_and_id(current_user, request.args, 'user_id', strict=False)
    if user:
        scope_filter = 'users_only'
        default_from = (datetime.now() - timedelta(days=365*10)).strftime("%Y-%m-%d")
    client = ClientGetterService.extract_from_user_and_id(current_user, request.args, 'client_id', strict=False)
    if client:
        scope_filter = 'clients_only'
        default_from = (datetime.now() - timedelta(days=365*10)).strftime("%Y-%m-%d")
    lead = LeadGetterService.extract_from_user_and_id(current_user, request.args, 'lead_id', strict=False)
    if lead:
        scope_filter = 'leads_only'
        default_from = (datetime.now() - timedelta(days=365*10)).strftime("%Y-%m-%d")
    if sender_user:
        default_from = (datetime.now() - timedelta(days=365*10)).strftime("%Y-%m-%d")
    from_date_str = request.form.get('from_date', request.args.get('from_date', ''))
    to_date_str = request.form.get('to_date', request.args.get('to_date', ''))
    search = request.form.get('search', request.args.get('search', ''))
    # Normalize to UTC naive to avoid implicit DB timezone conversions
    from_date = naiveDateTimeToStandard(from_date_str)
    to_date = naiveDateTimeToStandard(to_date_str)
    from_date_shifted = isoDateTimeToUTC(from_date_str) if from_date_str else None
    to_date_shifted = isoDateTimeToUTC(to_date_str) if to_date_str else None

    if scope_filter == '':
        if current_user.can_access('ViewAllMessages'):
            scope_filter = 'all'
        else:
            scope_filter = 'clients_users'

    if scope_filter == 'orphaned' and current_user.can_access('ViewOrphanedMessages') is False:
        flash('You cannot see orphaned messages. ')
        return redirect(url_for('index'))

    if scope_filter == 'all' and current_user.can_access('ViewAllMessages') is False:
        flash('You cannot see orphaned messages. ')
        return redirect(url_for('index'))

    entity = OperationalEntitiesGetterService.extract_from_user_and_id(current_user, request.args, 'shop_id', strict=False)
    if entity:
        scope_filter = 'clients_users'    

    pagination = Pagination.generate(request)

    pagination.objects = MessageGetterService.get_list(
        current_user,
        scope_filter=scope_filter,
        from_date=from_date_shifted,
        to_date=to_date_shifted,
        inout_filter=inout_filter,
        client=client,
        lead=lead,
        user=user,
        entity=entity,
        search=search,
        status=status_filter,
        sender_type=sender_type,
        sender_user=sender_user
    )

    MESSAGE_RECEIVERS_TOGGLE_MAP = {key: f".{key}" for key in MESSAGE_RECEIVERS}
    send_message_entity_category = request.args.get("send_message_entity_category")
    send_message_user = UserGetterService.extract_from_user_and_id(current_user, request.args, 'send_message_entity_id', strict=False) \
        if send_message_entity_category == "send_message_user" \
        else None
    send_message_client = ClientGetterService.extract_from_user_and_id(current_user, request.args, 'send_message_entity_id', strict=False) \
        if send_message_entity_category == "send_message_client" \
        else None
    send_message_lead = LeadGetterService.extract_from_user_and_id(current_user, request.args, 'send_message_entity_id', strict=False) \
        if send_message_entity_category == "send_message_lead" \
        else None
    
    select2 = {
        'client_id': {
            'items': ClientGetterService.get_list(current_user),
            'text': 'full_name',
            'selected': client,
            'person_search_field': True
        },
        'lead_id': {
            'items': LeadGetterService.get_list(current_user, unique_person=True),
            'text': 'full_name',
            'selected': lead,
            'person_search_field': True
        },
        'user_id': {
            'items': UserGetterService.get_list(current_user),
            'text': 'full_name',
            'selected': user,
            'person_search_field': True
        },
        'send_message_client_id': {
            'items': ClientGetterService.get_list(current_user),
            'text': 'full_name_and_id',
            'selected': send_message_client,
            'person_search_field': True
        },
        'send_message_lead_id': {
            'items': LeadGetterService.get_list(current_user, unique_person=True),
            'text': 'full_name_and_id',
            'selected': send_message_lead,
            'person_search_field': True
        },
        'send_message_user_id': {
            'items': UserGetterService.get_list(current_user),
            'text': 'full_name_and_id',
            'selected': send_message_user,
            'person_search_field': True
        },
        'sender_user_id': {
            'items': UserGetterService.get_list(current_user),
            'text': 'full_name_and_id',
            'selected': sender_user,
            'person_search_field': True
        }
    }
    
    return render('list_messages.html',
                  select2=select2,
                  client=client,
                  lead=lead,
                  user=user,
                  send_message_client=send_message_client,
                  send_message_lead=send_message_lead,
                  send_message_user=send_message_user,
                  pagination=pagination,
                  from_date=from_date,
                  to_date=to_date,
                  search=search,
                  scopeFilter=scope_filter,
                  inoutFilter=inout_filter,
                  status_filter=status_filter,
                  SMS_STATUS_MAP=SMS_STATUS_MAP,
                  SMS_STATUS_MAP_SHORT=SMS_STATUS_MAP_SHORT,
                  MESSAGE_RECEIVERS=MESSAGE_RECEIVERS,
                  MESSAGE_RECEIVERS_TOGGLE_MAP=MESSAGE_RECEIVERS_TOGGLE_MAP,
                  send_message_entity_category=send_message_entity_category,
                  SENDER_USER_TYPES=SENDER_USER_TYPES,
                  sender_type=sender_type,
                  sender_user=sender_user)
