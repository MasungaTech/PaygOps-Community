from pony.orm import db_session

from constants import API_PREFIX
from shared.api_helpers.api_structure import API_STRUCTURE
from shared.api_helpers.documented_resource import DocumentedResource
from shared.api_helpers.model_definition_base import ModelDefinitionMixin


def _get_example(schema, name=''):
    example = ModelDefinitionMixin.get_example(schema)
    if example is None:
        raise Exception(f'No example found for {name} - {schema}')
    return example

class TestAPIDefinition:

    ALLOWED_404 = ["/hook_subscription/delete", '/issues/<int:issue_id>/notes']
    ALLOWED_400 = ["/payments/odyssey"]
    OPEN_API_TO_FLASK_MAPPING = {
        'integer': 'int'
    }#Those ones are not according to standard, to be changed
    CONVS_EXAMPLES = {
        'int': '123',
        'string': 'string'
    }
    SPECIAL_VARIABLES_MAPPING = {
        'serial_number': 'path',
        'device_serial_number': 'path'
    }

    @db_session
    def test_api_definition(self, api_client, admin_api_key):

        for resource, endpoint in API_STRUCTURE.items():
            if issubclass(resource, DocumentedResource):
                if not resource.PUBLIC:
                    continue
                definition = resource.docs_get_metadata()
                for method, method_data in definition.items():
                    if method_data.get('deprecated'):
                        continue
                    data = {}
                    try:
                        headers = {
                            'Authorization': 'Bearer ' + admin_api_key
                        }
                        path = API_PREFIX + endpoint
                        for param in (method_data.get('parameters', []) or []):
                            assert param.get('name'), "Param without name"
                            assert param.get('description'), f"No description for param {param['name']}"
                            example = param.get('example')
                            if example is None:
                                example = param['schema'].get('example')
                                if example is None and param.get('examples'):
                                    example = list(param['examples'].keys())[0]
                            assert example is not None, f"No example for parameter {param['name']}"
                            if param['in'] == 'path':
                                name = param['name']
                                type = self.OPEN_API_TO_FLASK_MAPPING.get(param['schema']['type'], param['schema']['type'])
                                if name in self.SPECIAL_VARIABLES_MAPPING:
                                    type = self.SPECIAL_VARIABLES_MAPPING[name]
                                path = path.replace(f'<{type}:{name}>', example)
                        if '<' in path:
                            raise Exception(f'Unconverted variable in {path}')
                        request_body = method_data['requestBody'] or {}
                        schemas = [{}]
                        assert not request_body or 'schema' in request_body, "Request body defined but without schema"
                        if 'schema' in request_body:
                            if 'oneOf' in request_body['schema'] and 'properties' not in request_body['schema']:
                                schemas = request_body['schema']['oneOf']
                            elif 'anyOf' in request_body['schema'] and 'properties' not in request_body['schema']:
                                schemas = request_body['schema']['anyOf']
                            else:
                                schemas = [request_body['schema']]
                        for c,resp in method_data['responses'].items():
                            assert resp.get('description'), f"No description for response {c}"
                            assert resp.get('content'), f"No content for response {c}"
                        for schema in schemas:
                            request_data_info = schema['properties'].items() if schema else []
                            data = {
                                prop: _get_example(info, prop) for prop, info in request_data_info if not info.get('deprecated', False)
                            }
                            # Use the resolved path (with converted path parameters) instead of the raw endpoint
                            response = getattr(api_client, method)(path, headers=headers, json=data)
                            assert endpoint in self.ALLOWED_404 or '<' in endpoint or 404 not in (method_data['responses'] or [])
                            assert endpoint in self.ALLOWED_400 or response.status_code != 400 or response.json['error'] != "INVALID_REQUEST_DATA_SCHEMA", response.json['error_message']
                            if not (response.status_code == 404 and self.ALLOWED_404):
                                assert response.status_code in (method_data['responses'] or []), str(response.json) + '\n' + f'{endpoint} - {method}'
                    except Exception as e:
                        print(f"{endpoint} - {method} failed with {e}")
                        print(data)
                        print(definition[method])
                        raise e
                