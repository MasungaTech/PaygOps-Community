from flask_restful import Resource

API_ERROR_SCHEMA = {
    "type": "object",
    "properties": {
        "error": {
            "description": "The code of the error",
            "type": "integer",
            "format": "error-code",
            "example": 404
        },
        "error_message": {
            "description": "Description of the error ",
            "type": "string",
            "example": "Not Found"
        },
        "error_data": {
            "description": "Extra data related to the error",
            "type": "object",
            "example": {"numberOfDays": 10}
        },
        "success": {
            "description": "Boolean flag indicating if the operation succeeded",
            "type": "boolean",
            "example": False
        }
    }
}

EMPTY_JSON_ANSWER_SCHEMA = {
    "application/json": {
        "schema": {
            "type": "object",
            "properties": {}
        },
        "example": {}
    }
}


def get_error_example(code=404, message='Not found.', data=None):
    return {
        "error": code,
        "error_message": message,
        "error_data": data or {},
        "success": False
    }

class DocumentedResource(Resource):

    _methods = ['get', 'post', 'patch', 'delete', 'put']
    _services = {
        'get': ['GET_SERVICE', 'LIST_SERVICE'],
        'post': ['EDIT_SERVICE', 'ADD_SERVICE'],
        'delete': ['DELETE_SERVICE']
    }
    FORCED_DOCS = []
    PUBLIC = True
    VIEW_DOCS_PERMISSION = []
    META = {}
    ALLOWED_API_CALLER = [] # list of methods available for API caller
    API_CALLER_GENERATORS = {}
    SUBACTIONS = {}

    @classmethod
    def docs_get_metadata(cls, user=None):
        metadata = {}
        for method in cls._methods:
            if cls._should_be_documented(method):
                schema = cls.docs_extract_property(method, 'schema')
                permissions = cls.docs_extract_property(method, 'permissions')
                if permissions and user and not user.can_access_in_any(permissions, for_api_docs=True): continue
                metadata[method] = {
                    "deprecated": cls.docs_extract_property(method, 'deprecated', False),
                    "summary": cls.docs_extract_property(method, 'summary', method+cls.__name__),
                    "description": cls.docs_extract_property(method, 'description', cls.docs_extract_property(method, 'summary', method+cls.__name__)),
                    "permissions": permissions,
                    "tags": cls.docs_extract_property(method, 'tags', ["Miscellaneous"]),
                    "consumes": cls.docs_extract_property(method, 'consumes'),
                    "parameters": cls.docs_extract_property(method, 'parameters'),
                    "requestBody": cls.docs_extract_property(method, 'requestBody', {'schema': schema} if schema else None),
                    "responses": cls.docs_extract_property(method, 'responses')
                }
        return metadata

    @classmethod
    def docs_extract_property(cls, method, prop, default=None):
        meta = cls.get_meta()
        return meta[method].get(prop) or default if method in meta else default

    @classmethod
    def get_meta(cls):
        return cls.META

    @classmethod
    def _should_be_documented(cls, method):
        services = cls._services.get(method, [])
        defined = all([not hasattr(cls, s) or getattr(cls, s) is not None for s in services])
        return hasattr(cls, method) and (method in cls.FORCED_DOCS or defined)
