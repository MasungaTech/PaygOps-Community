def get_object_changes(old, new):
    if old:
        return {}
    diffs = {}
    old_data = old.get_serialized_object()
    new_data = new.get_serialized_object()
    schema = new.get_model_schema()['properties']

    def formatter(val):
        if isinstance(val, bool):
            return 'Yes' if val else 'No'
        return val

    for prop, new in new_data.items():
        if not schema[prop].get('comparable', True):
            continue
        name = schema[prop].get('name', prop)
        old = old_data[prop]
        if new != old:
            diffs[name] = [formatter(new), formatter(old)]
    return diffs