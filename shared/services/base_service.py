import copy
from shared.services.audit_log_service import AuditLogService


class BaseService:

    @classmethod
    def _add_from_data_and_user(cls, data, user, **kwargs):
        raise NotImplementedError

    @classmethod
    def _edit_from_data_and_user(cls, obj, data, user, **kwargs):
        raise NotImplementedError

    @classmethod
    def _delete_from_object_and_user(cls, obj, user, **kwargs):
        raise NotImplementedError

    @classmethod
    def add_from_data_and_user(cls, data, user, **kwargs):
        original_data = copy.deepcopy(data)
        result = cls._add_from_data_and_user(data, user, **kwargs)
        if isinstance(result, list): # this multiple adding is done for stock movements
            for obj in result:
                AuditLogService.store_audit_log_data(
                    user=user, data=original_data, action='add', object=obj
                )
        else:
            AuditLogService.store_audit_log_data(
                user=user, data=original_data, action='add', object=result
            )
        return result

    @classmethod
    def edit_from_data_and_user(cls, obj, data, user, **kwargs):
        original_data = copy.deepcopy(data)
        result = cls._edit_from_data_and_user(obj, data, user, **kwargs)
        AuditLogService.store_audit_log_data(
            user=user, data=original_data, object=obj, action='edit'
        )
        return result

    @classmethod
    def delete_from_object_and_user(cls, obj, user, skip_log=False, **kwargs):
        object_id = int(obj.id)
        object_type = str(object.__class__.__name__)
        result = cls._delete_from_object_and_user(obj, user, **kwargs)
        if not skip_log:
            AuditLogService.store_audit_log_data(
                user=user, object_id=object_id, object_type=object_type, action='delete'
            )
        return result
