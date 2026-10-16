from datetime import datetime
from shared.services.base_getter_service import BaseGetterService
from pony import orm
from shared.model.activity_log_model import ActivityLogEntry
from shared.services.sorter import Sorter
from shared.helpers.user_agent_parser import RequestUserAgentParser


class ActivityLogService:
    
    @classmethod
    def insert(cls, request, data, app, user):
        ActivityLogEntry(
            time=datetime.now(),
            user=user.id if user else 0,
            ip=request.environ.get('HTTP_X_REAL_IP', request.remote_addr),
            path=request.path,
            method=request.method,
            args=request.args,
            data=data,
            app=app,
            user_agent=RequestUserAgentParser.get_short_agent_string(request)
        )
        
class ActivityLogSorter(Sorter):
    
    def real_field_sort(field_name, desc=False):
        options = {
            'time': lambda l: l.time,
            'user': lambda l: l.user.full_name,
            'page': lambda l: l.path,
            'method': lambda l: l.method
        }
        options_desc = {
            'time': lambda l: orm.desc(l.time),
            'user': lambda l: orm.desc(l.user.full_name),
            'page': lambda l: orm.desc(l.path),
            'method': lambda l: orm.desc(l.method)
        }
        obj = options_desc if desc else options
        return obj.get(field_name, lambda l: l.time)


class ActivityLogGetter(BaseGetterService):

    OBJ_NAME = 'Activity Log'

    @classmethod
    def get_filtered_objects(cls, current_user, threshold=None, last_id=None, **kwargs):
        if current_user and not current_user.can_access(['ViewActivityLogAdmin', 'SuperAdmin']):
            return ActivityLogEntry.select(lambda a: 1 == 0)
        objects =  ActivityLogEntry.select()
        if threshold:
            objects = objects.filter(lambda l: l.time < threshold)
        if last_id:
            objects = objects.order_by(lambda l: l.id).filter(lambda l: l.id <= last_id)
        return objects