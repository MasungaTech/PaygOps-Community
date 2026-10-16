

import string


def nested_dict_format(my_string, my_dict):
    return DotNotationFormatter().format(my_string, **DictToObject(my_dict).__dict__ )

# Example usage with both dictionaries and objects
class DictToObject:
    def __init__(self, d):
        """Recursively converts a dictionary to an object."""
        for key, value in d.items():
            if isinstance(value, dict):
                setattr(self, key, DictToObject(value))
            else:
                setattr(self, key, value)

class DotNotationFormatter(string.Formatter):
    def get_value(self, key, args, kwargs):
        # Split the key by '.' to support dot notation for nested attributes or keys
        if isinstance(key, str):
            keys = key.split('.')
            value = kwargs
            for k in keys:
                if isinstance(value, dict):
                    value = value[k]  # Accessing dictionary
                else:
                    value = getattr(value, k)  # Accessing object attribute
            return value
        return string.Formatter.get_value(self, key, args, kwargs)


def insert_after_key(d, key, new_items):
    new_dict = {}
    for k, v in d.items():
        new_dict[k] = v
        if k == key:
            new_dict.update(new_items)  # Insert multiple new items here
    return new_dict

def rename_key(d, old_key, new_key):
    d = insert_after_key(d, old_key, {new_key: d[old_key]})
    del d[old_key]
    return d