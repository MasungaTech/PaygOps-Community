

from shared.api_helpers.query_parameters_validator import QueryParametersValidator
from shared.api_helpers.api_structure import API_STRUCTURE


class TestParametersBaseAPIClases:

    EXAMPLES = {
        ''
    }

    def test_parameters_validate_examples(self):
        for resource in API_STRUCTURE:
            if hasattr(resource, 'MODEL'):
                params = resource.MODEL.PARAMETERS
                for param in params:
                    for example in param['examples'].values():
                        QueryParametersValidator.validate_and_decode({
                            p['name']: p['schema'].get('default') if p != param else example['value'] for p in params
                        }, params)
