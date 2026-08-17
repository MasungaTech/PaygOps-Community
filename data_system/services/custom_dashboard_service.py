from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
import jwt
import time
from shared.services.settings_service import SettingsService


class CustomDashboardService:

    CUSTOM_DASHBOARDS = {
        'overview': {'default_view': 'overview.display_overview_default'},
        'contract': {'default_view': 'contract.view_contract_dashboard_default'},
        'demographic': {'default_view': 'client.view_clients_demographics_dashboard_default'},
        'aftersales': {'default_view': 'interaction_report.customer_support_dashboard_default'},
        'sales': {'default_view': 'sales_dashboard.sales_dashboard_default'},
        'accounting': {'default_view': 'account.payments_dashboard_default'},
        'mobile': {}
    }

    @classmethod
    def get_iframe_url_for_dashboard(cls, dashboard_name, current_user=None, entity=None, user=None, dashboard_data=None):
        dashboard_data = dashboard_data if dashboard_data else cls._get_dashboard_data(dashboard_name)
        metabase_url = SettingsService.get_setting('MetabaseURL')
        metabase_key = SettingsService.get_setting('MetabaseKey')

        dashboard_id = dashboard_data.get('id')
        if not dashboard_id or not metabase_key:
            return None
        filtered_parameters = cls._get_filtered_parameters(dashboard_data)

        parameters = cls._generate_extra_parameters(current_user=current_user, entity=entity, user=user, filtered_parameters=filtered_parameters)
        token = cls._generate_token(dashboard_id, metabase_key, parameters)
        iframe_url = metabase_url + "/embed/dashboard/" + token + "#theme=transparent&bordered=false&titled=false"
        iframe_url += '&hide_parameters='+','.join(filtered_parameters) if filtered_parameters else ''
        return iframe_url

    @classmethod
    def get_clean_name_for_dashboard(cls, dashboard_name):
        dashboard_data = cls._get_dashboard_data(dashboard_name)
        name = dashboard_data.get('name')
        return name or dashboard_name.capitalize()
    
    @classmethod
    def should_show_user_filter(cls, dashboard_name):
        dashboard_data = cls._get_dashboard_data(dashboard_name)
        if dashboard_data and dashboard_data.get('filter_user'):
            return True
        return False

    @classmethod
    def should_show_custom_dashboard(cls, dashboard_name):
        dashboard_data = cls._get_dashboard_data(dashboard_name)
        if dashboard_data and dashboard_data.get('enabled') and dashboard_data.get('id'):
            return True
        return False

    @classmethod
    def should_show_entity_filter(cls, dashboard_name):
        dashboard_data = cls._get_dashboard_data(dashboard_name)
        if dashboard_data and dashboard_data.get('filter_entity'):
            return True
        return False

    @classmethod
    def replaces_default(cls, dashboard_name):
        dashboard_data = cls._get_dashboard_data(dashboard_name)
        if dashboard_data and dashboard_data.get('replaces_default'):
            return True
        return False

    @classmethod
    def get_custom_dashboards_list(cls):
        return [name for name in cls.CUSTOM_DASHBOARDS]

    @classmethod
    def get_default_view(cls, dashboard_name):
        return cls.CUSTOM_DASHBOARDS.get(dashboard_name, {}).get('default_view')

    @classmethod
    def _get_dashboard_data(cls, dashboard_name):
        return SettingsService.get_setting('CustomDashboards').get(dashboard_name, {})

    @classmethod
    def _get_filtered_parameters(cls, dashboard_data):
        filtered_parameters = []
        if dashboard_data.get('filter_entity'):
            filtered_parameters.append('entity')
        if dashboard_data.get('filter_user'):
            filtered_parameters.append('user')
        return filtered_parameters

    @classmethod
    def _generate_extra_parameters(cls, current_user=None, entity=None, user=None, filtered_parameters=None):
        extra_parameters = {}
        if not filtered_parameters:
            filtered_parameters = []
        entities = []
        all = False
        if entity:
            entities = entity.descendants
        else:
            if current_user.can_access_in_all('ViewClients'):
                all = True
            else:
                entities = OperationalEntitiesGetterService.get_filtered_objects(current_user, level=0)

        if 'entity' in filtered_parameters:
            if not all:
                entity_ids = [entity.id for entity in entities] or [-1]
                extra_parameters.update({'entity': entity_ids})
        if 'user' in filtered_parameters:
            if user:
                extra_parameters.update({'user': user.id})

        return extra_parameters

    @classmethod
    def _generate_token(cls, dashboard_id, secret_key, parameters):
        payload = {
            "resource": {"dashboard": int(dashboard_id)},
            "params": parameters,
            "exp": round(time.time()) + (60 * 60 * 24) # 24h expiration
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")
        return token
        