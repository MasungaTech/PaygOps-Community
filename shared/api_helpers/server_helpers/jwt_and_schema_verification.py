import re
import dateutil
from constants import NAMED_PATTERNS
from functools import wraps
from shared.services.settings_service import SettingsService
from shared.logger.loggers import Error, LogAPI
from flask import current_app, request
import jwt
from jsonschema import validate, ValidationError, FormatChecker
from jsonschema._format import _checks_drafts
from pony.orm import db_session
from werkzeug.exceptions import Forbidden, Unauthorized, UnsupportedMediaType
from core_system.users.models.user_model import User
from shared.services.access_log_service import AccessLogService
from core_system.role.permissions import synthetic_permissions
from shared.services.translation_service import TranslationService
import config


@_checks_drafts(name="date-time")
def is_datetime(instance):
    if not isinstance(instance, str) or not instance:
        return True
    try:
        dateutil.parser.parse(instance)
    except:
        return False
    return True

def validate_schema(payload, schema, error_prefix=''):
    
    # We check if there's JSON in the payload
    if payload is None:
        raise UnsupportedMediaType('Payload does not contain JSON.')

    if schema is not None:
        try:
            validate(payload, schema, format_checker=FormatChecker())
        except ValidationError as error:
            msg = error.args[0].replace(r'\\', '\\')
            if error.absolute_path:
                path = [str(x) for x in error.absolute_path]
                msg = 'Error in '+".".join(path)+", "+msg
            if error.validator == 'pattern' and error.validator_value in NAMED_PATTERNS:
                msg = msg.replace("'"+error.validator_value+"'", NAMED_PATTERNS[error.validator_value]+" pattern")
            # The errors can't be translated as we need them to be standard for API use, they shouldnt be shown to users directly. 
            raise Error(TranslationService.make_notranslate(error_prefix+msg), code="VALIDATION_ERROR") from error

def get_user_from_request():
    # Auth validation
    auth_header = request.headers.get('Authorization')
    auth_token = None
    if auth_header:
        try:
            auth_token = auth_header.split(" ")[1]
        except IndexError:
            raise Unauthorized('Invalid token. Please log in again.')
    if not auth_token:
        raise Unauthorized('No JWT token provided')

    # We check the JWT signature
    request.environ['token_payload'] = check_and_load_jwt(auth_token)
@db_session
def check_and_load_jwt(auth_token): 
    secret = config.secret_key
    try:
        auth_decoded = jwt.decode(auth_token, secret, algorithms=['HS256'])
        user = User.get(id=auth_decoded['sub'])
        if  user and not user.active:
            raise Unauthorized('User is not active. Please contact support.')
        return auth_decoded
    except jwt.ExpiredSignatureError:
        raise Unauthorized('Signature expired. Please log in again.')
    except jwt.InvalidTokenError:
        raise Unauthorized('Invalid token. Please log in again.')

def check_permissions_for_user(user, permissions, entity=None, person=None, in_scope=False, in_all=False):
    if user.id == 0: return
    banned = SettingsService.get_setting('APIBannedUsers').split(',')
    if str(user.id) in banned: raise Forbidden('Your user has been banned')
    if not permissions: return
    if not isinstance(permissions, list) and synthetic_permissions.get(permissions):
        permissions = synthetic_permissions[permissions]
    permissions = permissions if type(permissions)==list else [permissions]
    allowed = user.can_access_in_scope(permissions, in_all=in_all) if in_scope else user.can_access(permissions, entity=entity, person=person)
    if not user or not allowed:
        raise Forbidden('No sufficient permission. One of the following permissions is needed: '+str(permissions))

def validate_request(schema=None, validate_json=False, args_schema=None):
    # JSON Validation
    if schema is not None or validate_json:
        # We check if it is valid JSON
        try:
            json_payload = request.json
        except Exception as e:
            raise UnsupportedMediaType('Payload is not valid JSON.')
        
        # We check if payload is JSON and if it matches the expected schema (if specified)
        validate_schema(json_payload, schema, '')

    if args_schema is not None or validate_json:
        validate_schema(request.args, args_schema, 'Request Params do not match expected schema. Details: ')

def check_permissions(permissions=None, entity=None, person=None, in_scope=False, in_all=False):
    if permissions is not None:
        with db_session:
            # We only check permissions if it doesnt come from the gateway
            if request.environ['token_payload']['sub'] != 0:
                user = User.get(id=request.environ['token_payload']['sub'])
                if user.username == config.SYSTEM_EMAIL:
                    raise Forbidden('You are not allowed to access this resource.')
                check_permissions_for_user(user, permissions, entity=entity, person=person, in_scope=in_scope, in_all=in_all)
        try:
            with db_session:
                user_app = 'api_app'
                if request.headers.get('PaygOpsApp') == 'Web':
                    user_app = 'web_app'
                AccessLogService.insert(request, user_app, request.environ['token_payload']['sub'])
        except Exception as error:
            LogAPI.Fatal(error)
            print('Error while logging API request')                


def verify(permissions=None, schema=None, validate_json=False, **ignored):
    def decorator(f):
        if not callable(f):
            return f
        @wraps(f)
        def wrapper(*args, **kw):
            validate_request(schema=schema, validate_json=validate_json)
            check_permissions(permissions, schema, validate_json, in_scope=True)
            return f(*args, **kw)
        return wrapper
    return decorator



