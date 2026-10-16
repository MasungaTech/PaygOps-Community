import re


def to_camel_case(snake_str):
    components = snake_str.split('_')
    return components[0] + "".join(x.title() for x in components[1:])


def dict_to_camel_case(this_dict):
    for k,v in this_dict.items():
        this_dict[to_camel_case(k)] = this_dict.pop(k)
    return this_dict


def from_camel_case(camel_case):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_case)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def dict_from_camel_case(this_dict):
    for k,v in this_dict.items():
        this_dict[from_camel_case(k)] = this_dict.pop(k)
    return this_dict



