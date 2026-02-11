from datetime import datetime
import config


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