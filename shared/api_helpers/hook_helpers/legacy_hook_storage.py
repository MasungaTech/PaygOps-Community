import config
import json


def load_hook_data():
    try:
        hooks_file = open(config.HOOK_CONFIGURATION_FILE, "r")
    except FileNotFoundError:
        return {}
    hook_file_data = hooks_file.read()
    if hook_file_data == '':
        hook_data = {}
    else:
        hook_data = json.loads(hook_file_data)
    hooks_file.close()
    return hook_data


def write_hook_data(hook_data):
    hooks_file = open(config.HOOK_CONFIGURATION_FILE, "w+")
    hooks_file.write(json.dumps(hook_data))
    hooks_file.close()