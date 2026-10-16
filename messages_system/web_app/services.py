from core_system.users.services.user_getter_service import UserGetterService
from shared.services.base_getter_service import BaseGetterService
from pony.orm import desc, select

from shared.helpers.list_helpers import timePeriodHelper
from messages_system.models.sms_db import IncomingSMS, OutgoingSMS
from core_system.client.services.client_getter_service import ClientGetterService
from sales_system.leads.services.lead_getter_service import LeadGetterService


class MessageGetterService(BaseGetterService):

    OBJ_NAME = 'Message'

    @classmethod
    def get_filtered_objects(cls, current_user, scope_filter, inout_filter, client, user, entity, from_date=None, to_date=None, lead=None, search=None, status=None, sender_type=None, sender_user=None, **kwargs):
        

        if inout_filter == 'in':
            messages = IncomingSMS.select()
            if from_date:
                messages = messages.filter(lambda m: m.ReceptionTime >= from_date)
            if to_date:
                messages = messages.filter(lambda m: m.ReceptionTime < to_date)
            ordering = IncomingSMS.ReceptionTime
        else:
            messages = OutgoingSMS.select()
            if from_date:
                messages = messages.filter(lambda m: m.SendingTime >= from_date)
            if to_date:
                messages = messages.filter(lambda m: m.SendingTime < to_date)
            if sender_type == 'automation':
                messages = messages.filter(lambda m: m.sending_user is None)
            elif sender_type == 'manually_sent':
                messages = messages.filter(lambda m: m.sending_user is not None)
            if sender_user:
                messages = messages.filter(lambda m: m.sending_user == sender_user.id)
            ordering = OutgoingSMS.SendingTime

        if status:
            messages = messages.filter(lambda m: m.status == status)

        if search:
            clients = ClientGetterService.get_list(current_user, search=search) 
            leads = LeadGetterService.get_list(current_user, search=search)
            filtered_clients = select(c.person.id for c in clients)[:]
            filtered_leads = select(l.person.id for l in leads)[:]
            persons_ids = filtered_clients + filtered_leads
            return messages.filter(lambda m: m.person_id in persons_ids).order_by(desc(ordering))
        
        if scope_filter == 'all':
            return messages.order_by(desc(ordering))
        
        if scope_filter == 'orphaned':
            return messages.filter(lambda m: not m.person_id).order_by(desc(ordering))

        if client:
            persons_ids = [client.person.id]
        elif lead:
            persons_ids = [lead.person.id]
        elif user:
            persons_ids = [user.person.id]
        elif scope_filter == 'leads_only':
            leads = LeadGetterService.get_list(current_user, entity=entity)
            persons_ids = select(l.person.id for l in leads)[:]
        else:
            clients = ClientGetterService.get_list(current_user, entity=entity) if scope_filter in ['clients_users', 'clients_only'] else []
            users = UserGetterService.get_list(current_user, entity=entity) if scope_filter in ['clients_users', 'users_only'] else []
            clients_ids = select(l.person.id for l in clients)[:] if clients else []
            user_ids = select(l.person.id for l in users)[:] if users else []
            persons_ids = clients_ids + user_ids

        messages = messages.filter(lambda m: m.person_id in persons_ids)
        return messages.order_by(desc(ordering))
