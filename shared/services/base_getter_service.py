from shared.logger.loggers import Error
from werkzeug.exceptions import NotFound
from flask.helpers import flash
from shared.services.translation_service import TranslationService
from shared.services.base_service import BaseService


class BaseGetterService(BaseService):

    PK_NAME = 'id'
    OBJ_NAME = 'Object'

    @classmethod
    def raise_strict(cls, main_resource=False, user=None, **kwargs):
        properties_text = ' and '.join([f'{k} = "{v}"' for k,v in kwargs.items()])
        error_text = TranslationService.ftext('No {} found with {}. It may not exist anymore or you may not have permission to access it.', cls.OBJ_NAME, properties_text, user=user)
        raise NotFound(error_text) if main_resource else Error(error_text, code="OBJECT_NOT_FOUND")

    @classmethod
    def get_from_user_and_properties(cls, user, strict=False, main_resource=False, **kwargs):
        # The following if ensures that we only try to get an object if the propeties provided include at least one 
        # not null string or number to avoid getting object where obj.mobile_uuid == '' or similar cases that might fail
        # siletly if only one object match the condition even though the condition is not unique
        obj = cls.get_list(user).filter(**kwargs).get() if any([v for v in kwargs.values() if not isinstance(v, bool)]) else None
        if not obj and strict:
            cls.raise_strict(main_resource, user=user, **kwargs)
        return obj

    @classmethod
    def get_from_user_and_id(cls, user, id, strict=False, main_resource=False):
        return cls.get_from_user_and_properties(user, **{cls.PK_NAME: id}, strict=strict, main_resource=main_resource)
    
    @classmethod
    def extract_from_user_and_id(cls, user, data, key, strict=True, empty_allowed=True):
        object_id = data.get(key)
        obj = None
        if object_id:
            obj = cls.get_from_user_and_id(user, object_id)
        if (object_id and not obj) or (not object_id and not empty_allowed):
            if strict:
                raise Error(f'Incorrect value for {key} [{object_id}], object not found')
            flash(f'Incorrect value for {key} [{object_id}], object not found')
        return obj

    # This function handles the conversion from API/UI user input (like objects id) 
    # to python objects (proper db class object). The input should be the user input
    # and the output to be passed to get_list method.
    @classmethod
    def preprocess_list_filters(cls, user, **kwargs):
        return kwargs

    @classmethod
    def get_list(cls, current_user=None, output='objects', page=None, page_size=1000, model=None, ordered=False, **kwargs):
        objects = cls.get_filtered_objects(current_user, **kwargs)
        if ordered:
            objects = objects.order_by(1)
        if model:
            kwargs['model'] = model
        if page is not None:
            objects = objects.page(page, page_size)
        if output == 'dict':
            objects = objects[:] # We preload everything
            return [object.get_serialized_object(**kwargs) for object in objects]
        if output == 'objects':
            return objects
        return [getattr(obj, output) for obj in objects]

    @classmethod
    def get_list_for_mobile(cls, current_user, cached_ids, **kwargs):
        return cls.get_list(current_user) # Default behaviour, can be overridden

    @classmethod
    def get_filtered_objects(cls, current_user=None, **kwargs):
        raise NotImplementedError
