

from shared.api_helpers.api_structure import API_STRUCTURE
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll


class TestQueryParametersAreStrings:

    def test_query_parameters_are_strings(self):

        for endpoint in API_STRUCTURE:
            if issubclass(endpoint, BaseAPIResourceAll):
                for param, meta in endpoint.EXTRA_LIST_PARAMS.items():
                    self._check_schema(param, meta, endpoint)
    
    def _check_schema(self, param, meta, endpoint):
        if 'type' in meta['schema']:
            self._check_type(param, meta['schema']['type'], endpoint, meta['in'])
        if 'oneOf' in meta['schema'] or 'anyOf' in meta['schema']:
            options = meta['schema'].get('oneOf', meta['schema'].get('anyOf'))
            for option in options:
                self._check_type(param, option['type'], endpoint, meta['in'])
        
    def _check_type(self, param, type, endpoint, meta_in):
        if meta_in == 'query':
            assert type == 'string' or type == 'array', f"Parameter {param} in {endpoint.__name__} is of type {type} instead of string or array"

