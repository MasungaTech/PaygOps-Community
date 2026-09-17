import json
from flask import request, render_template
from config import AJAX_SELECT_THRESHOLD, AJAX_SELECT_CLASS
from shared.helpers.db_helpers import searchable_text
from shared.api_helpers.server_helpers.json_serialization import CustomJSONEncoder
from pony import orm
from pony.orm.asttranslation import TranslationError


def render(template=None, select2=None, **kwargs):
    if not template or ('source' in request.args and request.args['source'] in select2):
        excluded = request.args.get('excluded', None)
        select = select2[request.args['source']]
        items = select['items']
        search_field = select.get('search_field', select['text'])
        person_search_field = select.get('person_search_field', False)
        term = request.args.get('q', request.args.get('term', '')).lower()
        if person_search_field:
            if term.isdigit():
                search_int = int(term)
                exact_ids = orm.select(e.id for e in items if e.id == search_int or e.person.custom_id == term)[:]
            else:
                exact_ids = orm.select(e.id for e in items if e.person.custom_id == term)[:]
            term = searchable_text(term)
            final = items.filter(lambda item: term in item.person.searchable_name or item.id in exact_ids).limit(100)
        else:
            try:
                final = items.filter(lambda item: term in getattr(item, search_field).lower()).limit(100)
            except TranslationError:
                # Some computed properties cannot be translated to SQL by Pony.
                # Fall back to Python filtering instead of returning a 500 error.
                final = [
                    item for item in items
                    if term in str(getattr(item, search_field, '') or '').lower()
                ][:100]
        id_field = select.get('id', 'id')
        data = select.get('data', {})
        results = {
            'results': [
                {
                    'id': getattr(item, id_field),
                    'text': getattr(item, select['text']),
                    'data': {
                        k: _func_or_prop(getattr(item, data[k])) for k in data
                    }
                } for item in final if str(getattr(item, id_field)) != str(excluded)]
        }
        return json.dumps(results, cls=CustomJSONEncoder)
    
    kwargs['select2'] = {}
    for select in select2:
        items = select2[select]['items']
        get_length = lambda i: len(i) if isinstance(i, list) or isinstance(i, dict) or isinstance(i, set) else i.count()
        id_field = select2[select].get('id', 'id')
        if select2[select].get('force_ajax', False) or get_length(items) > AJAX_SELECT_THRESHOLD:
            if 'selected' in select2[select] and select2[select]['selected']:
                if isinstance(select2[select]['selected'], str) or isinstance(select2[select]['selected'], int):
                    select2[select]['selected'] = items.filter(lambda i: i.id == int(select2[select]['selected'])).first()
                if isinstance(select2[select]['selected'], tuple):
                    kwargs[select] = [select2[select]['selected']]
                else:
                    item = select2[select]['selected']
                    if isinstance(item,list):
                        kwargs[select] = item
                    else:
                        if not select2[select].get('data'):
                            kwargs[select] = [get_item(item, id_field, select2, select)]
                        else:
                            kwargs[select] = get_data_items([item], id_field, select2, select)
            else:
                kwargs[select] = []
            kwargs[select+'_ajax'] = AJAX_SELECT_CLASS
            kwargs['select2'][select+'_ajax'] = True
            if 'url' in select2[select]:
                kwargs[select+'_url'] = select2[select]['url']
        else:
            kwargs[select+'_ajax'] = ''
            kwargs['select2'][select+'_ajax'] = ''
            if select2[select].get('raw_format', False):
                kwargs[select] = items
            else:
                kwargs[select] = select2_get_items(select2, select, items)

    return render_template(template, **kwargs)


def select2_get_items(select2, select, items):
    id_field = select2[select].get('id', 'id')
    if not select2[select].get('data'):
        return [get_item(item, id_field, select2, select) for item in items]
    else:
        return get_data_items(items, id_field, select2, select)


def get_item(item, id_field, select2, select):
    return (getattr(item, id_field), getattr(item, select2[select]['text']))


def get_data_items(items, id_field, select2, select):
    data = select2[select]['data']
    data_items = {
        getattr(item, id_field): {'value': getattr(item, select2[select]['text'])} for item in items
    }
    for item in items:
        data_items[getattr(item, id_field)].update({k: _func_or_prop(getattr(item, data[k])) for k in data})
    return data_items


def _func_or_prop(var):
    return var() if hasattr(var, '__call__') else var
