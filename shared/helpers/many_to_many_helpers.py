

from constants import INTEGER_REQUIRED_OPTIONS
from shared.logger.loggers import Error


def _data_get(data, key):
    if hasattr(data, 'get'):
        return data.get(key)
    return getattr(data, key, None)


def get_create_many_to_many_ids(data, name, default=None):
    """Resolve many-to-many IDs on create: prefer add_{name}_ids, else legacy {name}_ids."""
    add_ids = _data_get(data, f'add_{name}_ids')
    if add_ids is not None:
        return add_ids
    legacy_ids = _data_get(data, f'{name}_ids')
    if legacy_ids is not None:
        return legacy_ids
    return default


def edit_many_to_many(object, name, data, objects, model_property=None):

    if not model_property:
        model_property = name

    add_ids = data.get(f'add_{name}_ids', [])
    remove_ids = data.get(f'remove_{name}_ids', [])
    if add_ids or remove_ids:
        common = set(add_ids) & set(remove_ids)
        if common:
            raise Error(f'The same Object was set to add and to remove to {name}')
    else:
        # This is to support legacy modes and UI where allowed by schema
        all_ids = data.get(f'{name}_ids', [])
        current_ids = [o.id for o in getattr(object, model_property)]
        add_ids = [a for a in all_ids if a not in current_ids]
        remove_ids = [a for a in current_ids if a not in all_ids]

    add_objects = objects.filter(lambda o: o.id in add_ids)
    getattr(object, model_property).add(add_objects)
    remove_objects = objects.filter(lambda o: o.id in remove_ids)
    getattr(object, model_property).remove(remove_objects)

def add_many_to_many_schema(schema, name, human_name, meaning, prop=None, value=None, allow_legacy=False):
    schema['properties'].update({
        f'{name}_ids': {
            "type": "array",
            "items": {
                "type": "integer"
            },
            "example": [1, 2, 3],
            "value": lambda o: value(o) if value else [c.id for c in getattr(o, prop or name)],
            "description": f"The list of ids of {human_name}. {meaning}"
        },
        f'add_{name}_ids': {
            "type": "array",
            "items": {
                "oneOf": INTEGER_REQUIRED_OPTIONS
            },
            "example": [1, 2, 3],
            "description": f"The list of ids to add to {human_name}"
        },
        f'remove_{name}_ids': {
            "type": "array",
            "items": {
                "oneOf": INTEGER_REQUIRED_OPTIONS
            },
            "example": [1, 2, 3],
            "description": f"The list of ids to remove from {human_name}"
        }
    })
    if allow_legacy:
        schema["create_forbidden"] += [f"remove_{name}_ids"]
        schema["create_no_docs"] = schema.get("create_no_docs", []) + [f"{name}_ids"]
        schema["edit_forbidden"] += []
        schema["edit_no_docs"] = schema.get("edit_no_docs", []) + [f"{name}_ids"]
        schema["view_forbidden"] += [f"add_{name}_ids", f"remove_{name}_ids"]
    else:
        schema["create_forbidden"] += [f"{name}_ids", f"remove_{name}_ids"]
        schema["edit_forbidden"] += [f"{name}_ids"]
        schema["view_forbidden"] += [f"add_{name}_ids", f"remove_{name}_ids"]
