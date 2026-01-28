import re
from time import time
import pytest
from shared.logger.loggers import Error
from web_app import app
from flask import url_for
from pony.orm import db_session

class TestViews:

    EXCLUDED_ENDPOINTS = [
        "custom_forms.get_l0_entities_ajax"
    ]

    def generate_parameters(self, rule):
        var_regex = re.compile(r'<(?:(int|string|float|path|uuid):)?([a-zA-Z_]+)>')
        params = {}
        for match in var_regex.findall(rule.rule):
            param_type, param_name = match
            if param_type == 'int':
                params[param_name] = 123 
            elif param_type == 'float':
                params[param_name] = 123.45
            elif param_type == 'uuid':
                params[param_name] = '123e4567-e89b-12d3-a456-426614174000'
            else:
                params[param_name] = 'testvalue'
        return params

    @pytest.mark.parametrize("rule,endpoint", [(rule, rule.endpoint) for rule in app.url_map.iter_rules() if "GET" in rule.methods and 'static' not in rule.endpoint])
    def test_view(self, rule, endpoint, super_admin_app, context):
        if endpoint in self.EXCLUDED_ENDPOINTS:
            return
        t = time()
        TIMEOUT = 10 # seconds
        with context:
            parameters = self.generate_parameters(rule)
            url = url_for(rule.endpoint, **parameters)
            print(url)
            try:
                response = super_admin_app.get(url)
                assert response is not None, f"No response from URL: {url}"
                assert response.status_code in [200, 302, 401, 404], f"Unexpected status code {response.status_code} for URL: {url}"
            except Error: pass
        if endpoint == 'api_caller':
            TIMEOUT = 25
        if (time()-t) > TIMEOUT: 
            raise TimeoutError(f'Timed out with {time()-t} seconds')
