from datetime import datetime, timedelta

from config import API_PREFIX, api_secret
from core_system.core_entities import db
from core_system.operational_entities.models import Village
from pony.orm import db_session
from sales_system.leads.models.lead import Lead
from sales_system.leads.models.lead_status import LeadStatus
from sales_system.leads.models.status_category import StatusCategory
from shared.api_helpers.server_helpers.jwt_generation import generate_jwt
from shared.services.settings_service import SettingsService


class TestLeadStatusesApi:

    @staticmethod
    def _auth(token):
        return {'Authorization': 'Bearer ' + token}

    def _get(self, api_client, token):
        return api_client.get(
            API_PREFIX + '/lead_statuses',
            headers=self._auth(token),
        )

    def _post(self, api_client, token, body):
        return api_client.post(
            API_PREFIX + '/lead_statuses',
            json=body,
            headers=self._auth(token),
        )

    @staticmethod
    def _view_only_token():
        user = db.User.get(username='view_only@test.com')
        return generate_jwt(
            user.id,
            ['ViewLeads'],
            'Solaris Offgrid',
            api_secret,
            expiration_time=datetime.now() + timedelta(days=1),
        )

    @staticmethod
    def _rows(category):
        return [
            {'id': status.id, 'name': status.name, 'color': status.color}
            for status in LeadStatus.select(lambda status: status.category == category).order_by(
                LeadStatus.order
            )
        ]

    @db_session
    def test_allowed_for_new_lead_follows_the_new_lead_rule(self, api_client, admin_api_key):
        convinced = LeadStatus.get(name='Very Interested')
        installed = LeadStatus.get(name='Installed')
        hesitating = LeadStatus.get(name='Hesitating')
        previous = SettingsService.get_setting('statusTransitionRestrictions')
        SettingsService.set_setting('statusTransitionRestrictions', {'1001': [convinced.id]})
        try:
            admin_response = self._get(api_client, admin_api_key)
            assert admin_response.status_code == 200, admin_response.json
            view_response = self._get(api_client, self._view_only_token())
            assert view_response.status_code == 200, view_response.json
        finally:
            SettingsService.set_setting('statusTransitionRestrictions', previous or {})

        def flags(payload):
            return {row['name']: row for row in payload}

        admin_rows = flags(admin_response.json)
        view_rows = flags(view_response.json)
        assert admin_rows['Very Interested']['allowed_for_new_lead'] is True
        assert admin_rows['Installed']['allowed_for_new_lead'] is False
        assert view_rows['Hesitating']['allowed_for_new_lead'] is True
        assert view_rows['Very Interested']['allowed_for_new_lead'] is False
        assert view_rows['Installed']['allowed_for_new_lead'] is False
        assert view_rows['Very Interested']['id'] == convinced.id
        assert view_rows['Hesitating']['category'] == 'to_be_convinced'
        assert view_rows['Installed']['category'] == 'installed'
        assert hesitating.id != convinced.id

    @db_session
    def test_post_replaces_only_the_sent_category(self, api_client, admin_api_key):
        original = self._rows(StatusCategory.to_be_convinced)
        awaiting_before = {status.name for status in LeadStatus.select(
            lambda status: status.category == StatusCategory.awaiting_information
        )}
        renamed = [dict(row) for row in original]
        renamed[0] = {**renamed[0], 'name': original[0]['name'] + ' renamed'}
        renamed.append({'name': 'MCP Test Status', 'color': 'teal'})
        try:
            response = self._post(api_client, admin_api_key, {'to_be_convinced': renamed})
            assert response.status_code == 200, response.json
            rows = {row['name']: row for row in response.json}
            assert original[0]['name'] + ' renamed' in rows
            assert rows['MCP Test Status']['category'] == 'to_be_convinced'
            assert rows['MCP Test Status']['allowed_for_new_lead'] is True
            assert awaiting_before <= set(rows)
        finally:
            restore = self._post(api_client, admin_api_key, {'to_be_convinced': original})
            assert restore.status_code == 200, restore.json

    def test_post_rejects_dropping_a_status_that_has_leads(self, api_client, admin_api_key):
        with db_session:
            used = next((status for status in LeadStatus.select() if status.leads.count()), None)
            if used:
                used_id = used.id
                category_code = StatusCategory.to_inv_dict()[used.category]
                kept = [row for row in self._rows(used.category) if row['id'] != used.id]
            else:
                used_id = None
                category_code = None
                kept = None
        if used_id is None:
            with db_session:
                village = Village.select().first().not_empty_code
            created = api_client.post(
                API_PREFIX + '/leads',
                json={
                    'name': 'Status',
                    'surname': 'Guard',
                    'village': village,
                    'generator': 1,
                    'gender': 'Male',
                    'status': 'Very Interested',
                    'preferred_phone_number': '+2341234123499',
                },
                headers=self._auth(admin_api_key),
            )
            assert created.status_code == 201, created.json
            with db_session:
                used = Lead.get(id=created.json['id']).status
                used_id = used.id
                category_code = StatusCategory.to_inv_dict()[used.category]
                kept = [row for row in self._rows(used.category) if row['id'] != used.id]
        kept.append({'name': 'MCP Replacement Status', 'color': 'gray'})
        response = self._post(api_client, admin_api_key, {category_code: kept})
        assert response.status_code == 400, response.json
        assert 'cannot be deleted' in response.json['error_message']
        with db_session:
            assert LeadStatus.get(id=used_id) is not None
            assert LeadStatus.get(name='MCP Replacement Status') is None
