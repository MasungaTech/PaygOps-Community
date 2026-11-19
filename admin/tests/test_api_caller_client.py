import pytest
from flask import url_for
from mock import Mock, patch
from munch import DefaultMunch
from pony.orm import db_session

from admin.services.api_caller_service import APICallerService
from core_system.client.services.client_edit_service import ClientEditService
from core_system.client.services.client_getter_service import ClientGetterService
from shared.services.bulk_upload_task_processors import BulkUploadTaskProcessors


class TestAPICallerClient:

    @db_session
    def test_client_action_available(self, super_admin_user):
        actions, subactions = APICallerService.get_action_list(super_admin_user())
        assert actions['ClientResource_post'] == 'Set Client Information'
        assert subactions['ClientResource_post'] == {
            'set_tags': 'Set Client Tags',
            'edit_tags': 'Add/remove Client Tags'
        }

    @db_session
    def test_csv_templates(self, super_admin_app, context):
        with context:
            def template(action):
                response = super_admin_app.get(url_for('admin.api_caller_csv_template', action=action))
                assert response.status_code == 200
                return response.data.decode().splitlines()

            columns, examples = template('ClientResource_post')
            assert columns.split(',').count('id*') == 1
            assert 'id' not in columns.split(',')
            assert 'custom_id' in columns.split(',')

            assert template('ClientResource_post:set_tags') == ['id*,tags', '1234,"tag1,tag2,tag3"']
            assert template('ClientResource_post:edit_tags') == [
                'id*,add_tags,remove_tags', '1234,"tag1,tag2,tag3","tag2,tag3"'
            ]

    # Rows are not inserted here: other tests rely on fixed IDs (e.g. Person[1]) and on
    # Client.select().first(), which break if clients are created this early in the run.
    @pytest.mark.parametrize('action, body', [
        ('ClientResource_post', {'custom_id': 'A12345678', 'note': 'Edited in bulk'}),
        ('ClientResource_post:set_tags', {'tags': ['tag1', 'tag2']}),
        ('ClientResource_post:edit_tags', {'add_tags': ['tag1'], 'remove_tags': ['tag2']}),
    ])
    @db_session
    def test_processing_edits_client(self, super_admin_user, action, body):
        user = super_admin_user()
        client = Mock()
        with patch.object(ClientGetterService, 'get_from_user_and_id', return_value=client) as get_client, \
                patch.object(ClientEditService, 'edit_from_data_and_user') as edit_client:
            BulkUploadTaskProcessors.api_caller(
                [{'id': 1234}, body, 1],
                DefaultMunch(user=user.id, action=action)
            )
        get_client.assert_called_once_with(user, 1234, strict=True, main_resource=True)
        edit_client.assert_called_once_with(client, body, user)
