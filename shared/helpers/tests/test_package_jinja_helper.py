import json

import jinja2

from shared.helpers.package_jinja_helper import (
    escape_runtime_jinja_templates,
    is_package_step_reference,
    is_user_journey_package_file,
)


def _render_package_json(data, **context):
    escaped = escape_runtime_jinja_templates(data)
    rendered = jinja2.Template(
        json.dumps(escaped),
        undefined=jinja2.StrictUndefined,
    ).render(**context)
    return json.loads(rendered)


class TestPackageJinjaHelper:
    def test_identifies_package_step_references(self):
        assert is_package_step_reference('{{s1.uuid}}')
        assert is_package_step_reference('{{s02.form_id}}')
        assert not is_package_step_reference('{{platform_url}}')
        assert not is_package_step_reference('https://{{platform_url}}/tasks/')

    def test_identifies_user_journey_package_files(self):
        assert is_user_journey_package_file('s4-create_user_journey_versions.json')
        assert is_user_journey_package_file('nested/s04-create_user_journey_versions.json')
        assert not is_user_journey_package_file('s3-create_automations.json')
        assert not is_user_journey_package_file('manifest.json')

    def test_wraps_runtime_templates_and_keeps_package_step_refs(self):
        data = {
            'automation_uuid': '{{s1.uuid}}',
            'form_id': '{{s02.form_id}}',
            'redirect_url': 'https://{{platform_url}}/tasks/?assigned_to={{run_steps.finish.user_id}}',
        }

        escaped = escape_runtime_jinja_templates(data)

        assert escaped['automation_uuid'] == '{{s1.uuid}}'
        assert escaped['form_id'] == '{{s02.form_id}}'
        assert escaped['redirect_url'] == (
            'https://{% raw %}{{platform_url}}{% endraw %}/tasks/'
            '?assigned_to={% raw %}{{run_steps.finish.user_id}}{% endraw %}'
        )

    def test_is_idempotent(self):
        value = 'https://{{platform_url}}/tasks/?assigned_to={{run_steps.finish.user_id}}'
        escaped_once = escape_runtime_jinja_templates(value)
        escaped_twice = escape_runtime_jinja_templates(escaped_once)
        assert escaped_once == escaped_twice

    def test_survives_strict_jinja_render_during_package_install(self):
        data = {
            'steps': [
                {'data': {'automation_uuid': '{{s1.uuid}}'}},
                {'data': {'form_id': '{{s2.form_id}}'}},
                {
                    'data': {
                        'redirect_url': (
                            'https://{{platform_url}}/tasks/?assigned_to={{run_steps.finish.user_id}}'
                        )
                    }
                },
                {'data': {'redirect_url': '{{run_steps.finish.data.item_redirect_url}}'}},
            ]
        }

        rendered = _render_package_json(
            data,
            s1={'uuid': 'auto-1'},
            s2={'form_id': 42},
        )

        assert rendered['steps'][0]['data']['automation_uuid'] == 'auto-1'
        assert rendered['steps'][1]['data']['form_id'] == '42'
        assert rendered['steps'][2]['data']['redirect_url'] == (
            'https://{{platform_url}}/tasks/?assigned_to={{run_steps.finish.user_id}}'
        )
        assert rendered['steps'][3]['data']['redirect_url'] == '{{run_steps.finish.data.item_redirect_url}}'
