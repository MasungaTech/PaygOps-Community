from constants import INTEGER_OPTIONAL_OPTIONS_STRING
import dateutil
import json
from flask_restful import request, MethodNotAllowed
from flask import has_request_context
from werkzeug.exceptions import Forbidden
from pony import orm
from shared.api_helpers.query_parameters_validator import QueryParametersValidator
from shared.api_helpers.server_helpers.jwt_and_schema_verification import check_permissions, check_permissions_for_user, validate_schema
from shared.api_helpers.documented_resource import EMPTY_JSON_ANSWER_SCHEMA, DocumentedResource, API_ERROR_SCHEMA, get_error_example
from shared.logger.loggers import AcceptedWithProcessingError, AlreadyExistsError, LogAPI
from shared.logger.loggers import Error
from core_system.users.services.current_user_service import get_current_api_user
from shared.services.access_log_service import AccessLogService
from shared.helpers.date_helper import use_custom_date


class BaseAPIResourceAll(DocumentedResource):
    LIST_SERVICE = None
    ADD_SERVICE = None
    DELETE_SERVICE = None
    LIST_PERMISSION = None
    ADD_PERMISSION = None
    DELETE_PERMISSION = None
    MODEL = None
    USE_PARENT_MODEL = True
    ALTERNATE_MODEL_DEFINITION = None
    TAG = ''
    DEFAULT_OBJECTS = False
    DEFAULT_PAGE_SIZE = 1000
    LIST_VARIABLE = 'id'
    LIST_VARIABLE_TYPE = 'integer'
    LIST_VARIABLE_FORMAT = ''
    LIST_VARIABLE_EXAMPLES = [1234, 1235, 1236]
    EXTRA_LIST_PARAMS = {}
    EXTRA_POST_PARAMS = {}
    DEPRECATED = []
    FILTERS = {}
    ENTITY_REQUIRED = True
    CUSTOM_ORDER = False
    GLOBAL_DB_SESSION = True
    ALWAYS_SHOW_OBJECTS = False
    NO_PAGINATION = False
    LIST_DESCRIPTION = None
    ADD_DESCRIPTION = None
    ADD_SUMMARY = None

    @classmethod
    def _decode_arg_value(cls, value, schema):
        if value is None or not schema:
            return value
        if 'oneOf' in schema:
            if isinstance(value, str) and ',' in value:
                array_options = [opt for opt in schema['oneOf'] if opt.get('type') == 'array']
                for option in array_options:
                    decoded = cls._decode_arg_value(value, option)
                    if decoded is not None:
                        return decoded
            for option in schema['oneOf']:
                if option.get('type') != 'array':
                    return cls._decode_arg_value(value, option)
            return cls._decode_arg_value(value, schema['oneOf'][0])
        if schema.get('type') == 'array':
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                stripped = value.strip()
                if stripped.startswith('[') and stripped.endswith(']'):
                    try:
                        # Try parsing as JSON (requires double quotes)
                        parsed = json.loads(stripped)
                        if isinstance(parsed, list):
                            return parsed
                    except Exception:
                        # If JSON parsing fails, try parsing as Python-style list (single quotes)
                        try:
                            stripped_content = stripped[1:-1].strip()
                            if not stripped_content:
                                return []
                            # Split by comma, handling quoted values
                            items = []
                            current_item = ""
                            in_quotes = False
                            quote_char = None
                            for char in stripped_content:
                                if char in ["'", '"'] and (not in_quotes or char == quote_char):
                                    if in_quotes:
                                        # End of quoted value
                                        items.append(current_item)
                                        current_item = ""
                                        in_quotes = False
                                        quote_char = None
                                    else:
                                        # Start of quoted value
                                        in_quotes = True
                                        quote_char = char
                                elif char == ',' and not in_quotes:
                                    if current_item.strip():
                                        items.append(current_item.strip())
                                        current_item = ""
                                else:
                                    current_item += char
                            if current_item.strip() or in_quotes:
                                items.append(current_item.strip())
                            # Clean up items (remove any remaining quotes)
                            cleaned = [item.strip("'\"") for item in items if item.strip()]
                            return cleaned if cleaned else QueryParametersValidator.decode(stripped_content, schema)
                        except Exception:
                            stripped_content = stripped[1:-1]
                            return QueryParametersValidator.decode(stripped_content, schema)
            return QueryParametersValidator.decode(value, schema)
        return value

    @classmethod
    def _coerce_request_args(cls, args_schema):
        args_payload = {key: request.args.get(key) for key in request.args.keys()}
        properties = args_schema.get('properties', {}) if args_schema else {}
        for name, schema in properties.items():
            if name in args_payload and args_payload[name] is not None:
                args_payload[name] = cls._decode_arg_value(args_payload[name], schema)
        return args_payload

    @classmethod
    def process_extra_params(cls, kwargs, path_only=False, list=True, source_args=None):
        if source_args is not None:
            source = source_args
        elif has_request_context():
            source = request.args
        else:
            source = {}
        if not list:
            result = {}
        else:
            result = {k: v for k,v in cls.FILTERS.items()}
        for k, data in cls.EXTRA_LIST_PARAMS.items():
            if not path_only or data.get('in') == 'path':
                value = source.get(data['name']) if data.get('in') == 'query' else kwargs.get(data['name'])
                if value and data.get('schema') and data['schema'].get('format') == 'date-time':
                    value = dateutil.parser.parse(value)
                if not value and 'default' in data['schema']:
                    value = data['schema']['default']
                if data.get('in') == 'path' and 'properties' in data:
                    try:
                        value = {
                            p: converter(value) for p, converter in data['properties'].items()
                        }
                        for k, v in value.items():
                            result[k] = v
                    except ValueError as e:
                        raise Error(e if getattr(e, 'NOTRANSLATE', None) else str(e)) from e
                else:
                    result[k] = value

        return result

    EXTRA_RESPONSES = {}

    @orm.db_session(optimistic=False)
    @use_custom_date
    def get(self, **kwargs):
        if not self.LIST_SERVICE:
            raise MethodNotAllowed
        default_args = {}
        if not self.NO_PAGINATION:
            default_args.update({
                "page": {
                    "oneOf": INTEGER_OPTIONAL_OPTIONS_STRING
                },
                "page_size": {
                    "oneOf": INTEGER_OPTIONAL_OPTIONS_STRING
                }
            })
        if not self.ALWAYS_SHOW_OBJECTS:
            default_args.update({
                "include_objects": {
                    "type": "string",
                    "enum": ['true', 'false', 'True', 'False']
                }
            })
        args_schema = {
            'type': "object",
            "properties": {**{
                v['name']: v['schema'] for v in self.EXTRA_LIST_PARAMS.values()
            }, **default_args}, "additionalProperties": False
        }
        coerced_args = self._coerce_request_args(args_schema)
        validate_schema(coerced_args, args_schema, 'Request Params do not match expected schema. Details: ')
        if self.LIST_PERMISSION:
            check_permissions(permissions=self.LIST_PERMISSION, in_scope=True)
        include_objects = request.args.get('include_objects', str(self.DEFAULT_OBJECTS))
        if include_objects:
            include_objects = include_objects.lower() == 'true'
        try:
            page = max(1, int(request.args.get('page')))
            page_size = int(request.args.get('page_size', self.DEFAULT_PAGE_SIZE))
        except (ValueError, TypeError):
            page = None
            page_size = 1000
        extra_params = self.LIST_SERVICE.preprocess_list_filters(
            get_current_api_user(), **self.process_extra_params(kwargs, source_args=coerced_args))
        return self.LIST_SERVICE.get_list(
            model=self.MODEL if self.USE_PARENT_MODEL else None,
            current_user=get_current_api_user(),
            page=page,
            page_size=page_size,
            output='dict' if include_objects or self.ALWAYS_SHOW_OBJECTS else self.LIST_VARIABLE,
            ordered=True if not self.CUSTOM_ORDER else False,
            alternate_model=self.ALTERNATE_MODEL_DEFINITION,
            **extra_params,
        )

    @classmethod
    @orm.db_session
    def validate_post(cls, user, params, data):
        user = user.reload()
        validate_schema(
            data,
            cls.MODEL.get_model_schema(op='create', for_validate=True, alternate_model=cls.ALTERNATE_MODEL_DEFINITION) if cls.USE_PARENT_MODEL else None,
        )
        entity = None
        if hasattr(cls.ADD_SERVICE, 'get_affected_entity'):
            entity = cls.ADD_SERVICE.get_affected_entity(data, user, **params)
            if not entity and cls.ENTITY_REQUIRED:
                raise Exception('Entity not found')
        if cls.ADD_PERMISSION:
            check_permissions_for_user(
                user,
                permissions=cls.ADD_PERMISSION,
                entity=entity,
                in_scope=not cls.ENTITY_REQUIRED,
                in_all=not cls.ENTITY_REQUIRED
            )

    @classmethod
    def core_post(cls, user, params, data, args=None):
        extra_params = cls.process_extra_params(params, path_only=True, list=False)
        cls.validate_post(user, extra_params, data)
        try:
            if cls.GLOBAL_DB_SESSION:
                with orm.db_session:
                    this_object = cls.ADD_SERVICE.add_from_data_and_user(data, user.reload(), **extra_params)
                    orm.commit() # to get the id
            else:
                this_object = cls.ADD_SERVICE.add_from_data_and_user(data, user)
        except AcceptedWithProcessingError as error:
            return error.data, 202
        except AlreadyExistsError as error:
            return error.data, 200
        except Error as error:
            if hasattr(cls.ADD_SERVICE, 'get_human_readable_message'):
                with orm.db_session:
                    error_message = cls.ADD_SERVICE.get_human_readable_message(error, user=user.reload())
                if error_message:
                    raise Error(error_message, code=error.code)
            raise error
        extra_data = {}
        if isinstance(this_object, tuple):
            this_object, extra_data = this_object
        model = cls.MODEL if cls.USE_PARENT_MODEL else this_object.__class__
        with orm.db_session:
            if getattr(model, 'RAW_RESPONSE', False):
                return this_object, 201
            elif isinstance(this_object, list):
                response_data = [
                    obj.get_serialized_object(
                        model=model,
                        **model.parse_parameters(args or {}),
                        alternate_model=cls.ALTERNATE_MODEL_DEFINITION
                    ) for obj in this_object
                ]
            else:
                this_object = model.get(id=this_object.id) if getattr(model, 'NEEDS_RELOAD', False) else this_object
                response_data = this_object.get_serialized_object(model=model, **model.parse_parameters(args or {}), alternate_model=cls.ALTERNATE_MODEL_DEFINITION)
                response_data.update(extra_data)
                return response_data, 201

    @use_custom_date
    def post(self, **kwargs):
        if not self.ADD_SERVICE:
            raise MethodNotAllowed
        data = request.json
        user = get_current_api_user()
        if user.username == 'system@solarisoffgrid.com':
            raise Forbidden('You are not allowed to access this resource.')
        try:
            user_app = 'api_app'
            if request.headers.get('PaygOpsApp') == 'Web':
                user_app = 'web_app'
            with orm.db_session:
                AccessLogService.insert(request, user_app, user.id)
        except Exception as error:
            LogAPI.Fatal(error)
            print('Error while logging API request')
        return self.core_post(user, kwargs, data, request.args)
    
    @classmethod
    @orm.db_session
    def core_delete(cls, user, data, params):
        if not data:
            raise Error("No data provided.")

        # Attempt to find the list of IDs (first list of ints in the data)
        id_list = None
        for key, value in data.items():
            if isinstance(value, list) and all(isinstance(v, int) for v in value):
                id_list = value
                break

        if not id_list:
            raise Error("No valid list of integer IDs found in request body.")

        for item_id in id_list:
            obj = cls.MODEL.get(id=item_id)
            if not obj:
                continue  # Or raise Error if you prefer strict deletion

            # Permission check
            if cls.DELETE_PERMISSION:
                entity = cls.DELETE_SERVICE.get_entity_from_object(obj)
                check_permissions_for_user(
                    user,
                    permissions=cls.DELETE_PERMISSION,
                    entity=entity,
                    in_scope=not cls.ENTITY_REQUIRED,
                    in_all=not cls.ENTITY_REQUIRED
                )

            cls.DELETE_SERVICE.delete_from_object_and_user(obj, user)


    @use_custom_date
    def delete(self, **kwargs):
        if not self.DELETE_SERVICE:
            raise MethodNotAllowed

        data = request.json
        user = get_current_api_user()
        if user.username == 'system@solarisoffgrid.com':
            raise Forbidden('You are not allowed to access this resource.')

        try:
            user_app = 'api_app'
            if request.headers.get('PaygOpsApp') == 'Web':
                user_app = 'web_app'
            with orm.db_session:
                AccessLogService.insert(request, user_app, user.id)
        except Exception as error:
            LogAPI.Fatal(error)
            print('Error while logging API request')

        with orm.db_session:
            self.core_delete(user, data, kwargs)
            return {}, 204


    @classmethod
    def get_meta_get(cls):
        default_name = cls._get_default_name()
        default_args = []
        if not cls.NO_PAGINATION:
            default_args += [{
                "in": "query",
                "name": "page",
                "description": "The page number",
                "required": False,
                "schema": {
                        "type": "integer",
                        "example": 3
                }
            }, {
                "in": "query",
                "name": "page_size",
                "description": "The number of items per page",
                "required": False,
                "schema": {
                        "type": "integer",
                        "default": cls.DEFAULT_PAGE_SIZE,
                        "example": 100
                }
            }]
        if not cls.ALWAYS_SHOW_OBJECTS:
            default_args.append({
                "in": "query",
                "name": "include_objects",
                "description": f"Flag for including {default_name} object information (`true`) or just the {cls.LIST_VARIABLE} (`false`). **IMPORTANT:** When `true`, the use of pagination is compulsory, with a maximum page size of 1000. ",
                "required": False,
                "schema": {
                        "type": "boolean",
                        "default": cls.DEFAULT_OBJECTS,
                        "example": True
                }
            })
        object_schema = {**{"title": default_name + " Object"}, **cls.MODEL.get_model_schema(alternate_model=cls.ALTERNATE_MODEL_DEFINITION)} if cls.MODEL else {}
        meta = {
            "deprecated": "get" in cls.DEPRECATED,
            "tags": [cls.TAG],
            "permissions": cls._element_to_list(cls.LIST_PERMISSION),
            "summary": "LIST " + default_name + " Objects",
            "description": cls.LIST_DESCRIPTION if cls.LIST_DESCRIPTION else 'Used to list '+default_name+' objects.',
            "parameters": default_args + [v for v in cls.EXTRA_LIST_PARAMS.values()],
            "responses": {
                200: {
                    "description": "Returns List of "+default_name+" objects",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": object_schema if cls.ALWAYS_SHOW_OBJECTS else {
                                        "oneOf": [
                                            {
                                                "type": cls.LIST_VARIABLE_TYPE,
                                                "format": cls.LIST_VARIABLE_FORMAT
                                            },
                                            object_schema
                                        ]
                                }
                            },
                            "examples": {
                                "List of objects": {
                                    "summary": "",
                                    "value": [cls.MODEL.get_model_example(alternate_model=cls.ALTERNATE_MODEL_DEFINITION) if cls.MODEL else {}]
                                }
                            } if cls.ALWAYS_SHOW_OBJECTS else {
                                "include_objects == false": {
                                    "summary": "",
                                    "value": cls.LIST_VARIABLE_EXAMPLES,
                                },
                                "include_objects == true":  {
                                    "summary": "",
                                    "value": [cls.MODEL.get_model_example(alternate_model=cls.ALTERNATE_MODEL_DEFINITION) if cls.MODEL else {}]
                                }
                            }
                        }
                    },
                },
                400: {
                    "description": "Incorrect Request Data/Format",
                    "content": {
                        "application/json": {
                            "schema": API_ERROR_SCHEMA,
                            "example": get_error_example(400, "Invalid page format.")
                        }
                    }
                }
            }
        }
        return meta

    @classmethod
    def get_meta_post(cls):
        default_name = cls._get_default_name()
        return {
            "deprecated": "post" in cls.DEPRECATED,
            "tags": [cls.TAG],
            "permissions": cls._element_to_list(cls.ADD_PERMISSION),
            "summary": "ADD " + default_name + " Object" if not cls.ADD_SUMMARY else cls.ADD_SUMMARY,
            "description": cls.ADD_DESCRIPTION.replace('\n', '<br>') if cls.ADD_DESCRIPTION else 'Used to add '+default_name+' object.',
            "requestBody": {
                "description": default_name+" Model with at least the required properties",
                "schema": cls.MODEL.get_model_schema(op="create", alternate_model=cls.ALTERNATE_MODEL_DEFINITION) if cls.MODEL else {}
            },
            "parameters": [v for v in cls.EXTRA_POST_PARAMS.values()],
            "responses": {**{
                201: {
                    "description": "Returns Created "+default_name+" Information",
                    "content": {
                        "application/json": {
                            "schema": cls.MODEL.get_model_schema(alternate_model=cls.ALTERNATE_MODEL_DEFINITION) if cls.MODEL else {}
                        }
                    }
                },
                200: {
                    "description": "If the "+default_name+" was already created, it returns the information",
                    "content": {
                        "application/json": {
                            "schema": cls.MODEL.get_model_schema(alternate_model=cls.ALTERNATE_MODEL_DEFINITION) if cls.MODEL else {}
                        }
                    }
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
            }, **cls.EXTRA_RESPONSES.get('post', {})}
        }
    

    @classmethod
    def get_meta_delete(cls):
        default_name = cls._get_default_name()
        return {
            "deprecated": "delete" in cls.DEPRECATED,
            "tags": [cls.TAG],
            "permissions": [cls.DELETE_PERMISSION],
            "summary": f"DELETE {default_name} Object",
            "description": f"Used to delete one or more {default_name} objects. Accepts a JSON body containing a list of integer IDs under any key.",
            "requestBody": {
                "description": default_name+" Model with at least the required properties",
                "schema": cls.MODEL.get_model_schema(op="create", alternate_model=cls.ALTERNATE_MODEL_DEFINITION) if cls.MODEL else {}
            },
            "responses": {
                204: {
                    "description": f"{default_name} deleted sucessfully",
                    "content": EMPTY_JSON_ANSWER_SCHEMA
                },
                400: {
                    "description": "Invalid request data or format",
                    "content": {
                        "application/json": {
                            "schema": API_ERROR_SCHEMA,
                            "example": get_error_example(400, "No valid list of integer IDs found in request body.")
                        }
                    }
                }
            }
        }



    @classmethod
    def get_meta_patch(cls):
        return {}

    @classmethod
    def get_meta(cls):
        return {
            'get': cls.get_meta_get(),
            'post': cls.get_meta_post(),
            'patch': cls.get_meta_patch(),
            'delete': cls.get_meta_delete(),
        }

    @classmethod
    def _get_default_name(cls):
        if getattr(cls, 'OBJECT_NAME', None):
            return cls.OBJECT_NAME
        return getattr(cls.MODEL, '__name__', cls.__name__.replace('Resource', '').replace('All', ''))
    

    @staticmethod
    def _element_to_list(x):
        return x if not x or isinstance(x, list) else [x]
