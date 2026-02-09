import json
import re
from datetime import datetime

from flask import current_app, has_request_context, request
from pony import orm

from shared.helpers.json_helpers import default_function
from shared.helpers.user_agent_parser import RequestUserAgentParser
from shared.model.activity_log_model import AuditLogEntry, db
from shared.services.sorter import Sorter


class AuditLogService:

    APP_NAMES = {
        'web_app': 'Web',
        'api_app': 'API',
        'mobile_sync_app': 'Mobile'
    }

    EXLUDED_TYPES = ['Permission', 'QuestionAnswerGroup', 'OldActivityLogEntry', 'Notification', 'Token', 'OfflineToken', 'PaymentWalletOwner', 'PersonEntityChange', 'Bill', 'BilledItem', 'AggregatedBilledItem', 'Metric', 'MetricType', 'QuestionText', 'QuestionChoiceText', 'AnwserGroup', 'HistoricalData', 'o']
    EXCLUDED_VIEW_TYPES  = EXLUDED_TYPES + ['MinimumPriceOffer', 'Answer', 'QuestionChoice', 'ReasonsForNotBuying', 'IssueTypeGroup', 'InteractionTopicGroup']
    EXTRA_TYPES = ['SettingList']
    NAME_MAP = {
        'PortfolioEntity': 'Portfolio',
        'UserWithRole': 'Operational Permission',
        'SurveyAnswer': 'Form Answer',
        'OrderedQuestion': 'Form Question',
        'ContractRepayment': 'Contract Payment',
        'SettingList': 'Multiple Settings',
        'MentorRequest': 'User Request',
        'ActivationRequest': 'Token Request',
        'Note': 'Issue Note'
    }

    @classmethod
    def store_audit_log_data(cls, user=None, data=None, object=None, action=None, object_type=None, object_id=None):
        # Might need to use raw SQL for insertion here
        data = json.loads(json.dumps(data, default=default_function))
        object_type, object_id = cls._get_object_type_and_id(object, object_type, object_id)
        data = cls._remove_password_from_data_if_needed(data, object_type)
        related_person_id = cls._get_related_person_id(object, object_type)
        with orm.db_session:
            log = AuditLogEntry(
                time=datetime.now(),
                user_id=user.id,
                object_type=object_type,
                object_id=object_id,
                related_person_id=related_person_id,
                action=action,
                data=data or {}
            )
            if has_request_context():
                platform=cls.APP_NAMES.get(current_app.name)
                headers_app=request.headers.get('PaygOpsApp')
                if platform == 'API' and headers_app:
                    platform = headers_app
                log.platform = platform or 'Other'
                log.request_uuid = request.headers.get('RequestUUID', '')
                log.user_agent = RequestUserAgentParser.get_short_agent_string(request)
                log.ip = str(request.environ.get('HTTP_X_REAL_IP', request.remote_addr))
                custom_date_header = request.headers.get('X-Custom-Date')
                if custom_date_header:
                    from freezegun.api import real_datetime
                    log.mocked_time = datetime.now()
                    log.time = real_datetime.now()
        return log

    @classmethod
    def get_list(cls, from_time=None, to_time=None, user_id=None, action=None, object_type=None, object_id=None, search_field=None, search_value=None, request_uuid=None):
        from shared.helpers.clock import Clock
        from shared.helpers.form_helpers import isoDateTimeToStandard

        logs = AuditLogEntry.select()

        if from_time:
            d = isoDateTimeToStandard(from_time)
            from_time_utc = Clock.localize_to_utc(d, naive=True)
            logs = logs.filter(lambda l: l.time >= from_time_utc)
        if to_time:
            d = isoDateTimeToStandard(to_time)
            to_time_utc = Clock.localize_to_utc(d, naive=True)
            logs = logs.filter(lambda l: l.time <= to_time_utc)

        if user_id and user_id != 'NONE':
            selected_user = int(user_id)
            logs = logs.filter(lambda l: l.user_id == selected_user)
        elif user_id:
            logs = logs.filter(lambda l: not l.user_id)

        if action:
            logs = logs.filter(lambda l: l.action == action)

        if request_uuid:
            logs = logs.filter(lambda l: l.request_uuid == request_uuid)

        related_person_id = None
        if object_type and object_id:
            related_person_id = cls._get_related_person_id(object_type=object_type, object_id=object_id)

        if related_person_id:
            logs = logs.filter(lambda l: (l.object_type == object_type and l.object_id == object_id) or l.related_person_id == related_person_id)
        else:
            if object_type:
                logs = logs.filter(lambda l: l.object_type == object_type)

            if object_id:
                logs = logs.filter(lambda l: l.object_id == object_id)

        if search_field and search_value:
            logs = logs.filter(lambda l: search_value.lower() in str(l.data[search_field]).lower())
        elif search_value:
            logs = logs.filter(lambda l: search_value.lower() in str(l.data).lower())

        return logs

    @classmethod
    def _get_object_type_and_id(cls, object=None, object_type=None, object_id=None):
        object_type=object.__class__.__name__ if object else object_type
        object_id=getattr(object, 'id', 0) if object else object_id
        return object_type, object_id

    @classmethod
    def _get_related_person_id(cls, object=None, object_type=None, object_id=None):
        REFERENCE_OBJECT_MAP = {
            'Lead': lambda o: o.person,
            'Client': lambda o: o.person,
            'User': lambda o: o.person,
            'LeadGenerator': lambda o: o.person,
            'Person': lambda o: o,
        }
        map_function = REFERENCE_OBJECT_MAP.get(object_type, None)
        if map_function:
            if not object:
                object = cls._get_object_from_type_and_id(object_type, object_id)
            if object:
                reference_object = map_function(object)
                if reference_object:
                    type, id = cls._get_object_type_and_id(object=reference_object)
                    return id
        return None

    @classmethod
    def _get_object_from_type_and_id(cls, object_type, object_id):
        return db.entities.get(object_type).get(id=object_id)

    @classmethod
    def get_object_type_name(cls, class_name):
        # Needs to be done there to avoid circular import
        from shared.services.settings_service import SettingsService
        cls.NAME_MAP.update({
            'Village': SettingsService.get_setting('OperationalEntities')[0]['name'],
            'Cluster': SettingsService.get_setting('OperationalEntities')[1]['name'],
            'Hub': SettingsService.get_setting('OperationalEntities')[2]['name'],
            'Zone': SettingsService.get_setting('OperationalEntities')[3]['name'],
            'Region': SettingsService.get_setting('OperationalEntities')[4]['name']
        })
        raw_name = cls.NAME_MAP.get(class_name, class_name)
        return ' '.join(re.findall('[A-Z][^A-Z]*', raw_name)) # We add spaces before Caps
    
    @staticmethod
    def _remove_password_from_data_if_needed(data, object_type):
        """Utility method to check and remove 'password' from data if the request is from the specific URL."""
        if object_type == 'APIKey':
            if 'password' in data:
                del data['password']
        return data
        

class AuditLogSorter(Sorter):

    @staticmethod
    def real_field_sort(field_name, desc=False):
        options = {
            'time': lambda l: l.time,
            'user': lambda l: l.user.full_name,
            'object': lambda l: l.object,
            'action': lambda l: l.action,
        }
        options_desc = {
            'time': lambda l: orm.desc(l.time),
            'user': lambda l: orm.desc(l.user.full_name),
            'object': lambda l: orm.desc(l.object),
            'action': lambda l: orm.desc(l.action),
        }
        obj = options_desc if desc else options
        return obj.get(field_name, lambda l: l.time)
