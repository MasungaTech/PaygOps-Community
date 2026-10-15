def compare_objs(obj1, obj2, path=''):
    if obj1 == obj2: return
    elif not isinstance(obj1, dict) or not isinstance(obj2, dict):
        if isinstance(obj1, list) and isinstance(obj2, list):
            l1, l2 = len(obj1), len(obj2)
            for i in range(0, min(l1, l2)):
                compare_objs(obj1[i], obj2[i], f'{path}.{i}')
            shorter = 'obj1' if l1 < l2 else 'obj2'
            larger = obj1 if l1 > l2 else obj2
            raise Exception(f'{shorter}{path} is missing last items: {larger[min(l1, l2):max(l1, l2)]}')
        raise Exception(f'obj1{path} is {obj1} and obj2{path} {obj2}')
    if obj1.keys() != obj2.keys():
        missing1 = obj2.keys()-obj1.keys()
        missing2 = obj1.keys()-obj2.keys()
        error = []
        if missing1: error.append(f'obj1{path} is missing {list(missing1)}')
        if missing2: error.append(f'obj2{path} is missing {list(missing2)}')
        raise Exception(', '.join(error))
    for k in obj1.keys():
        compare_objs(obj1[k], obj2[k], f'{path}.{k}')


def all_keys_are_in_list(dictionary, key_list):
    return all(key in key_list for key in dictionary)