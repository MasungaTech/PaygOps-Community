from http.client import UNSUPPORTED_MEDIA_TYPE
from pony import orm
from pony.orm.core import MultipleObjectsFoundError
from werkzeug.exceptions import Forbidden, BadRequest, NotFound
from flask_restful import request, MethodNotAllowed
from shared.api_helpers.server_helpers.jwt_and_schema_verification import check_permissions, check_permissions_for_user, validate_request, validate_schema
from shared.api_helpers.documented_resource import EMPTY_JSON_ANSWER_SCHEMA, DocumentedResource, API_ERROR_SCHEMA, get_error_example
from shared.logger.loggers import Error, LogAPI
from core_system.users.services.current_user_service import get_current_api_user
from shared.helpers.date_helper import use_custom_date
import dateutil

from shared.services.access_log_service import AccessLogService

class BaseAPIResourceIndividual(DocumentedResource):
    GET_SERVICE = None
    GET_GLOBAL_PERMISSION = None
    GET_PERMISSION = None
    GET_DESCRIPTION = None

    EDIT_SERVICE = None
    EDIT_GLOBAL_PERMISSION = None
    EDIT_PERMISSION = None
    EDIT_DESCRIPTION = None

    DELETE_GLOBAL_PERMISSION = None
    DELETE_SERVICE = None
    DELETE_PERMISSION = None
    OBJECT_NAME = 'Object'
    MODEL = None
    USE_PARENT_MODEL = True
    ALTERNATE_MODEL_DEFINITION = None
    TAG = ''
    ID_PARAM = {
        "name": "id",
        "description": "The unique id of the "+OBJECT_NAME,
        "in": "path",
        "required": True,
        "example": "1234",
        "schema": {
            "type": "integer"
        }
    }
    DEPRECATED = []
    EXTRA_PARAMS = {}
    MULTIPLE_OBJECTS_FOUND_ERROR = 'Multiple {OBJECT_NAME}s found with the same ID'
    ALLOW_UPSERT = False
    INSERT_ENDPOINT = None # to be provided if upsert allowed

    @classmethod
    def process_extra_params(cls, kwargs, path_only=False, include_id=False):
        result = {}
        params = cls.EXTRA_PARAMS
        if include_id:
            params = params | {'id': cls.ID_PARAM}
        for k, data in (params).items():
            if not path_only or data.get('in') == 'path':
                value = request.args.get(data['name']) if data.get('in') == 'query' else kwargs.get(data['name'])
                if value and data.get('schema') and data['schema'].get('format') == 'date-time':
                    value = dateutil.parser.parse(value)
                if not value and 'default' in data['schema']:
                    value = data['schema']['default']
                if value and value != '':
                    result[k] = value
        return result

    @classmethod
    def get_properties_from_id(cls, path_id):
        ''' This function converts from the id used in the url to the property or properties in the model usign a key: value syntax.'''
        if cls.ID_PARAM and 'properties' in cls.ID_PARAM:
            try:
                return {
                    p: converter(path_id) for p, converter in cls.ID_PARAM['properties'].items()
                }
            except ValueError as e:
                raise Error(e if getattr(e, 'NOTRANSLATE', None) else str(e)) from e
        return {
            cls.ID_PARAM.get("property", cls.ID_PARAM["name"]) if cls.ID_PARAM else 'id': path_id
        }
    
    @orm.db_session
    @use_custom_date
    def get(self, **kwargs):
        args_schema = {
            'type': "object",
            "properties": {**{
                v['name']: v['schema'] for v in list(self.EXTRA_PARAMS.values())+(self.MODEL.PARAMETERS if self.MODEL else [])
            }}, "additionalProperties": True
        }
        validate_request(args_schema=args_schema)
        if not self.GET_SERVICE:
            raise MethodNotAllowed
        try:
            id = kwargs[self.ID_PARAM["name"] if self.ID_PARAM else 'id']
            extra_params = self.GET_SERVICE.preprocess_list_filters(get_current_api_user(), **self.process_extra_params(kwargs)) if self.process_extra_params(kwargs) else {}
            this_object = self.GET_SERVICE.get_from_user_and_properties(get_current_api_user(), **self.get_properties_from_id(id), **extra_params, strict=True, main_resource=True)
        except MultipleObjectsFoundError:
            raise Error(self.MULTIPLE_OBJECTS_FOUND_ERROR.format(OBJECT_NAME=self.OBJECT_NAME), code="MULTIPLE_OBJECTS_FOUND")
        except Error as error:
            e = error
            raise BadRequest(e if getattr(e, 'NOTRANSLATE', None) else str(e))
        relevant_entity = self._get_relevant_entity(this_object)
        if not relevant_entity:
            if hasattr(self.GET_SERVICE, 'get_affected_entity'):
                try: data = request.json
                except: data = {}
                relevant_entity = self.GET_SERVICE.get_affected_entity(data, get_current_api_user(), **self.process_extra_params(kwargs, path_only=True, include_id=True))
            if hasattr(self.GET_SERVICE, 'get_entity_from_object'):
                relevant_entity = self.GET_SERVICE.get_entity_from_object(this_object)
        relevant_person = self._get_relevant_person(this_object)
        if not relevant_entity and not relevant_person and self.GET_GLOBAL_PERMISSION:
            check_permissions(self.GET_GLOBAL_PERMISSION, in_scope=True, in_all=True)
        else:
            check_permissions(permissions=self.GET_PERMISSION, entity=relevant_entity, person=relevant_person)
        model = self.MODEL if self.USE_PARENT_MODEL else this_object.__class__
        return this_object.get_serialized_object(model=model, **model.parse_parameters(request.args), individual_object=True, alternate_model=self.ALTERNATE_MODEL_DEFINITION)

    @classmethod
    def core_post(cls, user, params, data, args=None):
        validate_schema(data, cls.MODEL.get_model_schema(op='edit', for_validate=True, alternate_model=cls.ALTERNATE_MODEL_DEFINITION), '')
        try:
            id = params[cls.ID_PARAM["name"] if cls.ID_PARAM else 'id']
            extra_params = cls.GET_SERVICE.preprocess_list_filters(user, **cls.process_extra_params(params)) if cls.process_extra_params(params) else {}
            this_object = cls.GET_SERVICE.get_from_user_and_properties(user, **cls.get_properties_from_id(id), **extra_params, strict=not cls.ALLOW_UPSERT, main_resource=True)
            if cls.ALLOW_UPSERT and not this_object:
                insert_data = {**data, **{
                    cls.ID_PARAM["name"] if cls.ID_PARAM else 'id': id
                }}
                return cls.INSERT_ENDPOINT.core_post(user, params, insert_data, args)
        except MultipleObjectsFoundError as exc:
            raise Error(
                cls.MULTIPLE_OBJECTS_FOUND_ERROR.format(OBJECT_NAME=cls.OBJECT_NAME),
                code="MULTIPLE_OBJECTS_FOUND"
            ) from exc
        if not this_object:
            raise NotFound(cls.OBJECT_NAME+' not found')
        relevant_entity = cls._get_relevant_entity(this_object)
        relevant_person = cls._get_relevant_person(this_object)
        if not relevant_entity and not relevant_person:
            if hasattr(cls.EDIT_SERVICE, 'get_affected_entity'):
                relevant_entity = cls.EDIT_SERVICE.get_affected_entity(request.get_json(), user, **cls.process_extra_params(params, path_only=True, include_id=True))
            if hasattr(cls.EDIT_SERVICE, 'get_entity_from_object'):
                relevant_entity = cls.EDIT_SERVICE.get_entity_from_object(this_object)
        if not relevant_entity and not relevant_person and cls.EDIT_GLOBAL_PERMISSION:
            check_permissions_for_user(user, cls.EDIT_GLOBAL_PERMISSION, in_scope=True, in_all=True)
        else:
            check_permissions_for_user(user, cls.EDIT_PERMISSION, entity=relevant_entity, person=relevant_person)
        try:
            cls.EDIT_SERVICE.edit_from_data_and_user(this_object, data, user)
        except Error as error:
            orm.rollback()
            if not hasattr(cls.EDIT_SERVICE, 'get_human_readable_message'):
                raise error
            error_message = cls.EDIT_SERVICE.get_human_readable_message(error, user=user)
            if not error_message:
                raise error
            raise Error(error_message, code=error.code, **error.data) from error
        except Exception as error:
            orm.rollback()
            raise error
        else:
            orm.commit()
            with orm.db_session:
                model = cls.MODEL if cls.USE_PARENT_MODEL else this_object.__class__
                this_object = model.get(id=this_object.id) if model.NEEDS_RELOAD else this_object
                return this_object.get_serialized_object(model=model, **model.parse_parameters(args or {}), individual_object=True, alternate_model=cls.ALTERNATE_MODEL_DEFINITION)

    @orm.db_session
    @use_custom_date
    def post(self, **kwargs):
        if not self.EDIT_SERVICE:
            raise MethodNotAllowed
        try: data = request.json
        except Exception: raise UNSUPPORTED_MEDIA_TYPE('Payload is not valid JSON.')
        user = get_current_api_user()
        self._insert_activity_log_entry(user)
        return self.core_post(user, kwargs, data, request.args)

    @classmethod
    def core_delete(cls, user, params):
        try:
            id = params[cls.ID_PARAM["name"] if cls.ID_PARAM else 'id']
            extra_params = cls.GET_SERVICE.preprocess_list_filters(user, **cls.process_extra_params(params)) if cls.process_extra_params(params) else {}
            this_object = cls.GET_SERVICE.get_from_user_and_properties(user, **cls.get_properties_from_id(id), **extra_params, strict=True, main_resource=True)
        except MultipleObjectsFoundError:
            raise Error(cls.MULTIPLE_OBJECTS_FOUND_ERROR.format(OBJECT_NAME=cls.OBJECT_NAME), code="MULTIPLE_OBJECTS_FOUND")
        except Error as error:
            e = error
            raise BadRequest(e if getattr(e, 'NOTRANSLATE', None) else str(e))
        if not this_object:
            raise NotFound(cls.OBJECT_NAME+' not found')
        relevant_entity = cls._get_relevant_entity(this_object)
        relevant_person = cls._get_relevant_person(this_object)
        if not relevant_entity and not relevant_person:
            if hasattr(cls.DELETE_SERVICE, 'get_affected_entity'):
                relevant_entity = cls.DELETE_SERVICE.get_affected_entity(request.get_json(), user, **cls.process_extra_params(params, path_only=True, include_id=True))
            if hasattr(cls.DELETE_SERVICE, 'get_entity_from_object'):
                relevant_entity = cls.DELETE_SERVICE.get_entity_from_object(this_object)
        if not relevant_entity and not relevant_person and cls.DELETE_GLOBAL_PERMISSION:
            check_permissions_for_user(user, cls.DELETE_GLOBAL_PERMISSION, in_scope=True, in_all=True)
        else:
            check_permissions_for_user(user, permissions=cls.DELETE_PERMISSION, entity=relevant_entity, person=relevant_person)
        cls.DELETE_SERVICE.delete_from_object_and_user(this_object, user)

    @orm.db_session
    @use_custom_date
    def delete(self, **kwargs):
        if not self.DELETE_SERVICE:
            raise MethodNotAllowed
        user = get_current_api_user()
        self._insert_activity_log_entry(user)
        self.core_delete(user, kwargs)
        return '', 204

    def _insert_activity_log_entry(self, user):
        if user.username == 'system@solarisoffgrid.com':
            raise Forbidden('You are not allowed to access this resource.')
        try:
            user_app = 'api_app'
            if request.headers.get('PaygOpsApp') == 'Web':
                user_app = 'web_app'
            AccessLogService.insert(request, user_app, request.environ['token_payload']['sub'])
        except Exception as error:
            LogAPI.Fatal(error)
            print('Error while logging API request')

    @classmethod
    def _get_relevant_person(cls, this_object):
        return None

    @classmethod
    def _get_relevant_entity(cls, this_object):
        return None

    @classmethod
    def get_meta(cls):
        def l(x):
            return x if isinstance(x, list) else [x] if x else []
        GET_TOTAL_PERMISSION = l(cls.GET_GLOBAL_PERMISSION) + l(cls.GET_PERMISSION) or None
        return {
            'get': {
                "deprecated": "get" in cls.DEPRECATED,
                "tags": [cls.TAG],
                "permissions": cls._element_to_list(GET_TOTAL_PERMISSION),
                "summary": "GET " + cls.OBJECT_NAME + " Object",
                "description": "" if not cls.GET_DESCRIPTION else cls.GET_DESCRIPTION,
                "parameters": [cls.ID_PARAM]+list(cls.EXTRA_PARAMS.values())+cls.MODEL.PARAMETERS,
                "responses": {
                    200: {
                        "description": "Returns "+cls.OBJECT_NAME+"'s Information",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "oneOf": [
                                        cls.MODEL.get_model_schema(**cls.MODEL.parse_parameters({param['name']: case['value']}), alternate_model=cls.ALTERNATE_MODEL_DEFINITION) for param in cls.MODEL.PARAMETERS for case in param.get('examples', {}).values()
                                    ],
                                } if cls.MODEL.PARAMETERS else cls.MODEL.get_model_schema(alternate_model=cls.ALTERNATE_MODEL_DEFINITION),
                                "example"+ ("s" if cls.MODEL.PARAMETERS else ""): {
                                    param['name']+key: {
                                        "summary": example['summary'],
                                        "value": cls.MODEL.get_model_example(**cls.MODEL.parse_parameters({param['name']: example['value']}), alternate_model=cls.ALTERNATE_MODEL_DEFINITION)
                                    } for param in cls.MODEL.PARAMETERS for key, example in param.get('examples', {}).items()
                                } if cls.MODEL.PARAMETERS else cls.MODEL.get_model_example(alternate_model=cls.ALTERNATE_MODEL_DEFINITION)
                            }
                        }
                    },
                    404: {
                        "description": cls.OBJECT_NAME+" Not Found",
                        "content": {
                            "application/json": {
                                "schema": API_ERROR_SCHEMA,
                                "example": get_error_example(message=cls.OBJECT_NAME+" Not Found")
                            }
                        },
                    },
                    400: {
                        "description": "Incorrect Request Data/Format",
                        "content": {
                            "application/json": {
                                "schema": API_ERROR_SCHEMA,
                                "example": get_error_example(400, "Invalid Id format.")
                            }
                        }
                    }
                }
            },
            'post': {
                "deprecated": "post" in cls.DEPRECATED,
                "tags": [cls.TAG],
                "permissions": cls._combine_nullable(cls.EDIT_PERMISSION, cls.EDIT_GLOBAL_PERMISSION),
                "summary": "EDIT " + cls.OBJECT_NAME + " Object",
                "description": "" if not cls.EDIT_DESCRIPTION else cls.EDIT_DESCRIPTION.replace('\n', '<br>'),
                "parameters": [cls.ID_PARAM],
                "requestBody": {
                    "description": cls.OBJECT_NAME+" Model with only the properties to edit",
                    "schema": cls.MODEL.get_model_schema(op="edit", alternate_model=cls.ALTERNATE_MODEL_DEFINITION) if cls.MODEL else {}
                },
                "responses": {
                    200: {
                        "description": "Returns "+cls.OBJECT_NAME+"'s Edited Information",
                        "content": {
                            "application/json": {
                                "schema": cls.MODEL.get_model_schema(alternate_model=cls.ALTERNATE_MODEL_DEFINITION) if cls.MODEL else {}
                            }
                        }
                    },
                    404: {
                        "description": cls.OBJECT_NAME+" Not Found",
                        "content": {
                            "application/json": {
                                "schema": API_ERROR_SCHEMA,
                                "example": get_error_example(message=cls.OBJECT_NAME+" Not Found")
                            }
                        },
                    },
                    400: {
                        "description": "Incorrect Request Data/Format",
                        "content": {
                            "application/json": {
                                "schema": API_ERROR_SCHEMA,
                                "example": get_error_example(400, "Invalid Id format.")
                            }
                        }
                    }
                }
            },
            'delete': {
                "deprecated": "delete" in cls.DEPRECATED,
                "tags": [cls.TAG],
                "permissions": cls._combine_nullable(cls.DELETE_PERMISSION, cls.DELETE_GLOBAL_PERMISSION),
                "summary": "DELETE " + cls.OBJECT_NAME + " Object",
                "parameters": [cls.ID_PARAM],
                "responses": {
                    204: {
                        "description": cls.OBJECT_NAME+" deleted sucessfully",
                        "content": EMPTY_JSON_ANSWER_SCHEMA
                    },
                    404: {
                        "description": cls.OBJECT_NAME+" Not Found",
                        "content": {
                            "application/json": {
                                "schema": API_ERROR_SCHEMA,
                                "example": get_error_example(message=cls.OBJECT_NAME+" Not Found")
                            }
                        },
                    },
                    400: {
                        "description": "Incorrect Request Data/Format",
                        "content": {
                            "application/json": {
                                "schema": API_ERROR_SCHEMA,
                                "example": get_error_example(400, "Invalid Id format.")
                            }
                        }
                    }
                }
            }
        }

    @staticmethod
    def _element_to_list(x):
        return x if not x or isinstance(x, list) else [x]

    @classmethod
    def _combine_nullable(cls, x, y):
        return (cls._element_to_list(x) or []) + (cls._element_to_list(y) or [])
