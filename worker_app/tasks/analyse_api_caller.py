from pony import orm
import json

from admin.services.api_caller_service import APICallerService
from core_system.users.models.user_model import User
from shared.api_helpers.server_helpers.jwt_and_schema_verification import \
    validate_schema
from shared.logger.loggers import Error
from shared.services.background_task_base import BackgroundTask
from worker_app.worker_app import worker_app


def schema_converter(d, schema, final=True):
    if 'type' in schema:
        t = schema['type']
        if t == 'integer' or (t == 'number' and schema.get('format') == 'int'):
            try:
                return int(d)
            except (ValueError, TypeError):
                pass
        if t == "number":
            try:
                return float(d)
            except (ValueError, TypeError):
                pass
        if t == "boolean":
            if isinstance(d, bool):
                return d
            if isinstance(d, str):
                normalized = d.lower().strip()
                if normalized in ['true', 'yes', '1']:
                    return True
                if normalized in ['false', 'no', '0']:
                    return False
            return None
        if t == "array":
            if not isinstance(d, str):
                return None
            if d == '':
                return []
            elif allows_integer(schema):
                return [int(x) for x in d.split(',')]
            return d.split(',')
    if 'oneOf' in schema:
        for option in schema['oneOf']:
            v = schema_converter(d, option, final=False)
            if v is not None:  # keep False / 0 / []
                return v
    if final:
        return d

@worker_app.task
@orm.db_session
def analyse_api_caller(task_uuid):

    print('Analysing API caller data...')

    task_service = BackgroundTask(task_uuid)
    user = User.get(id=task_service.user)
    docs = APICallerService.get_action_docs(
        task_service.action, user, error=Error('Action not available')
    )

    lines = list(task_service.read_csv_file())
    total_lines = len(lines)
    task_service.update_analysis_progress(0, total_lines, 'Starting analysis...')
    headers = [h.strip().replace('*', '') for h in task_service.headers]

    parameters_map = {}
    body_data_map = {}

    param_data = docs.get('parameters') or []
    param_schema = {
        "type": "object",
        "properties": {
            p['name']: p['schema'] for p in param_data
        }
    }
    request_body = docs.get('requestBody')
    schema = request_body.get('schema', {}) if request_body else {}
    possible_params = [p['name'] for p in param_data]
    param_types = {p['name']: p['schema']['type'] for p in param_data}
    joint_data = {
        **(schema.get('properties') or {}),
        **{k: v for opt in schema.get('oneOf', []) for k,v in opt['properties'].items()
    }}
    possible_data = list(schema.get('properties', {}).keys()) + [
        k for opt in schema.get('oneOf', []) for k in opt['properties'].keys()
    ]
    for i, h in enumerate(headers):
        if h in possible_params:
            parameters_map[h] = i
        if h in possible_data:
            body_data_map[h] = i

    data, errors = [], {}

    correct_rows = 0
    for line_number, line in enumerate(lines, start=1):

        if len(line) != len(headers):
            errors[line_number] = f'Line with incorrect format, it was expected to have {len(headers)} columns.'
            continue

        parameters = {
            p: line[i] if param_types[p] != 'integer' else int(line[i]) for p, i in parameters_map.items()
        }
        body_data = {p: schema_converter(line[i], joint_data[p]) for p, i in body_data_map.items()}

        for item, generator in docs['generators'].items():
            if item in possible_params and not item in parameters:
                parameters[item] = generator()
            if item in possible_data and not item in body_data:
                body_data[item] = generator()

        if 'subaction' in docs:
            presets = docs['subaction'].get('presets', {}).items()
            parameters.update({k:v for k,v in presets if k in possible_params})
            body_data.update({k:v for k,v in presets if k in possible_data})

        try:
            if parameters:
                validate_schema(parameters, param_schema, '')
            if body_data:
                validate_schema(body_data, schema, '')
        except Error as e:
            errors[line_number] = e.get_message()
            continue

        correct_rows += 1
        data.append([parameters, body_data, line_number])

        # Periodically update analysis progress
        if line_number % 25 == 0 or line_number == total_lines:
            task_service.update_analysis_progress(line_number, total_lines)

    task_service.complete_analysis({
        'correct_rows': correct_rows,
        'total_rows': total_lines,
        'errors': errors
    }, data)

def allows_integer(schema):
    items = schema.get('items', {})

    if isinstance(items, dict):
        # Case 1: Direct type
        if items.get('type') == 'integer':
            return True

        # Case 2: oneOf list
        if 'oneOf' in items:
            return any(option.get('type') == 'integer' for option in items['oneOf'])

    return False
