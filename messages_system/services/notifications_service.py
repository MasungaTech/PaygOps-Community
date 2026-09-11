from datetime import datetime
from shared.services.base_getter_service import BaseGetterService
from pony import orm
from messages_system.models.notification import Notification
from shared.services.settings_service import SettingsService
from shared.services.sorter import Sorter
from shared.helpers.html_safety_helper import join_markup, safe_var
from tests.support.mock_query import MockQuery
from core_system.core_entities import db


class NotificationsService(BaseGetterService):

    OBJ_NAME = 'Notification'

    @classmethod
    def get_filtered_objects(cls, current_user, unseen=False, search=None, **kwargs):
        if not current_user.can_access(['SeeHubNotificationsAdmin', 'SeeAllNotificationsAdmin']):
            return MockQuery([])
        notifications = Notification.select()
        if not current_user.can_access('SeeAllNotificationsAdmin'):
            notifications = notifications.filter(lambda n: n.operational_entity == current_user.shop)
        if unseen and current_user.last_notifications_time:
            notifications = notifications.filter(lambda n: n.time > current_user.last_notifications_time)
        if search:
            notifications = notifications.filter(lambda n: search.lower() in n.text.lower())
        return notifications

    @classmethod
    def update_last_seen(cls, user):
        user.last_notifications_time = datetime.now()

    @classmethod
    def add_notification(cls, text, endpoint='', params=[], url='', operational_entity=None):
        Notification(text=str(text), endpoint=endpoint, params=params, url=url, operational_entity=operational_entity)

    @classmethod
    def add_no_phone_notification(cls, obj):
        if not SettingsService.get_setting('LeadInfoSettings')['phone_number']['required']:
            return
        if isinstance(obj, db.Client):
            endpoint = 'client.edit_client'
            params = {'client_id': obj.id}
        elif isinstance(obj, db.Lead):
            endpoint = 'leads.view_lead'
            params = {'lead_id': obj.id}
        else:
            return
        cls.add_notification(
            text=join_markup('No phone number found for ', safe_var(obj.full_name), '. '),
            endpoint=endpoint,
            params=params,
            operational_entity=obj.person.village.parent.parent
        )

    @classmethod
    def add_deleted_status_notification(cls, obj):
        if isinstance(obj, db.Lead):
            endpoint = 'leads.view_lead'
            params = {'lead_id': obj.id}
        else:
            return
        cls.add_notification(
            text=join_markup(
                'The status set offline for Lead ',
                safe_var(obj.full_name),
                ' was removed. The lead was set to the first status of the category instead. ',
            ),
            endpoint=endpoint,
            params=params,
            operational_entity=obj.person.village
        )
    
    @classmethod
    def add_device_registered_notification(cls, lead, device, user):
        endpoint = 'leads.view_lead'
        params = {'lead_id': lead.id}
        cls.add_notification(
            text=join_markup(
                'The Device ',
                safe_var(device.get_display_name()),
                ' was already registered when it was offline registered by User ',
                safe_var(user.full_name),
                f' ({user.id}) with Lead ',
                safe_var(lead.full_name),
                f' ({lead.id})',
            ),
            endpoint=endpoint,
            params=params,
            operational_entity=lead.person.village.parent.parent
        )

    @classmethod
    def add_token_generation_error_notification(cls, device, details=''):
        details_part = join_markup(' Details: ', safe_var(details), '.') if details else ''
        shop = None
        if device.contract and device.contract.client.person.village.parent:
            shop = device.contract.client.person.village.parent.parent
        cls.add_notification(
            text=join_markup(
                'There was an error while generating a Token for device ',
                safe_var(device.get_display_name()),
                '.',
                details_part,
            ),
            endpoint='device.view_device',
            params={'device_id': device.id},
            operational_entity=shop
        )


class NotificationsSorter(Sorter):

    @staticmethod
    def real_field_sort(field_name, desc=False):
        options = {
            'time': lambda l: l.time,
            'text': lambda l: l.text,
            'shop': lambda l: getattr(l.shop, 'name', '')
        }
        options_desc = {
            'time': lambda l: orm.desc(l.time),
            'text': lambda l: orm.desc(l.text),
            'shop': lambda l: orm.desc(getattr(l.shop, 'name', '')),
        }
        obj = options_desc if desc else options
        return obj.get(field_name, lambda l: l.time)
