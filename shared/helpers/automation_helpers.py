from datetime import datetime
import config
from flask import request
from flask_login import AnonymousUserMixin
from pony.orm import db_session
from werkzeug.exceptions import Unauthorized

from core_system.users.models.user_model import User
from shared.api_helpers.server_helpers.jwt_and_schema_verification import check_and_load_jwt


def _coerce(val):
    if isinstance(val, datetime):
        return val.isoformat()
    return val

def automation_to_dict(automation, op="view", for_export=False):
    if not config.ENABLE_ENTERPRISE_FEATURES:
        raise RuntimeError("Automations are disabled in this edition.")
    from app_builder_system.automations.models.automation_model import Automation
    if automation is None:
        return None

    definition = Automation.get_model_definition(op=op, for_export=for_export)
    props = definition["properties"]
    # pick which set of fields to expose based on op
    allowed_key = {
        "view": "view_allowed",
        "edit": "edit_allowed",
        "create": "create_allowed",
    }.get(op, "view_allowed")
    allowed = definition.get(allowed_key, list(props.keys()))

    out = {}
    for key in allowed:
        spec = props.get(key, {})
        value_fn = spec.get("value")
        if callable(value_fn):
            val = value_fn(automation)
        else:
            # fallback to raw attribute
            val = getattr(automation, key, None)

        # ensure JSON-safe
        if isinstance(val, dict):
            out[key] = {k: _coerce(v) for k, v in val.items()}
        elif isinstance(val, list):
            out[key] = [_coerce(v) for v in val]
        else:
            out[key] = _coerce(val)

    return out


def _is_usable_user(user):
    if user is None:
        return False
    if isinstance(user, AnonymousUserMixin):
        return False
    is_anonymous = getattr(user, 'is_anonymous', False)
    if callable(is_anonymous):
        is_anonymous = is_anonymous()
    if is_anonymous:
        return False
    user_id = getattr(user, 'id', None)
    if user_id in (None, '', -1, 0):
        return False
    if hasattr(user, 'active') and not user.active:
        return False
    return True


def _user_from_id(user_id):
    if user_id is None or user_id == '':
        return None
    try:
        parsed_id = int(user_id)
    except (TypeError, ValueError):
        return None
    user = User.get(id=parsed_id)
    if user and user.active:
        return user
    return None


@db_session
def resolve_user_from_request_auth(session_user=None):
    """
    Resolve the logged-in PaygOps user for an automation run.

    Prefers the Flask session user, then a Bearer JWT (e.g. CUJ sendDataToAPI).
    """
    if _is_usable_user(session_user):
        return session_user

    auth_header = request.headers.get('Authorization') if request else None
    if not auth_header:
        return None

    parts = auth_header.split(' ', 1)
    if len(parts) != 2 or parts[0].lower() != 'bearer' or not parts[1]:
        return None

    try:
        payload = check_and_load_jwt(parts[1])
    except Unauthorized:
        return None
    except Exception:
        return None

    return _user_from_id(payload.get('sub'))


def resolve_automation_current_user(user=None):
    """Return the logged-in user to mint current_user_api_key, or None."""
    if _is_usable_user(user):
        return user
    return None
