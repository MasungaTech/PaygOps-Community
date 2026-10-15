import re
import pony.orm.core
from flask import has_request_context, request
from werkzeug.exceptions import UnsupportedMediaType

def is_hook_name(x):
    return isinstance(x, str) and re.match('^[a-z_]*$', x)

def get_skipped_hooks():
    if not has_request_context():
        return []
    arg_value = request.args.get('skip_hook', False)
    if not arg_value: 
        try:
            arg_value = request.json.get('skip_hook', False) if request.json and isinstance(request.json, dict) else False
        except UnsupportedMediaType:
            arg_value = False
        if not arg_value: 
            return []
    if arg_value in ['True', 'true', True]:
        return True
    if isinstance(arg_value, str) and re.match('^([a-z_]+,)*[a-z_]+$', arg_value):
        return arg_value.split(',')
    if isinstance(arg_value, list) and all([is_hook_name(x) for x in arg_value]):
        return arg_value
    return []

if hasattr(pony.orm.core.SessionCache, "patched"):
    pony.orm.core.SessionCache.patched += 1
else:
    pony.orm.core.SessionCache.patched = 1
    original_commit = pony.orm.core.SessionCache.commit
    original_rollback = pony.orm.core.SessionCache.rollback

    def new_commit(cache):
        original_commit(cache)
        if hasattr(cache, 'commit_hooks'):
            print(f'Executing {len(cache.commit_hooks)} hooks...')
            skipped_hooks = get_skipped_hooks()
            for event, hook in cache.commit_hooks.items():
                if skipped_hooks == True or event in skipped_hooks:
                    print(f'Event {event} set to be ignored, skipping hook...')
                    continue
                hook()
            cache.commit_hooks = {}
            print(f'Hook queue cleared')


    def new_rollback(cache):
        if hasattr(cache, 'commit_hooks'):
            cache.commit_hooks = {}
            print(f'Hook queue cleared')
        original_rollback(cache)

    pony.orm.core.SessionCache.commit = new_commit
    pony.orm.core.SessionCache.rollback = new_rollback

    def add_commit_hook(cache, id, hook):
        if not hasattr(cache, 'commit_hooks'):
            cache.commit_hooks = {}
        print('Hook appended to queue')
        cache.commit_hooks[id] = hook

    pony.orm.core.SessionCache.add_commit_hook = add_commit_hook
