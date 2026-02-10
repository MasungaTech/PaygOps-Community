import copy

from pony.orm import db_session, flush
import config

from shared.logger.loggers import Error
from core_system.operational_entities.services.client_group_getter_service import \
    ClientGroupGetterService
from core_system.operational_entities.services.operational_entities_getter import \
    OperationalEntitiesGetterService
from core_system.operational_entities.services.operational_entities_helper import \
    OperationalEntitiesHelper
from shared.services.base_service import BaseService
from shared.services.settings_service import SettingsService



class WebMenuService:

    @classmethod
    def get_operational_entities_menu(cls, user):
        OperationalEntitiesConfig = SettingsService.get_setting('OperationalEntities')
        entities = []
        if OperationalEntitiesConfig[4]['enabled'] and OperationalEntitiesGetterService.get_list(user, level=4).count() > 0:
            entities.append({
                'endpoint': 'entities.list_entities',
                'kwargs': {'level': 4},
                'micon': OperationalEntitiesHelper.get_icon(4),
                'label': OperationalEntitiesConfig[4]['names'],
                'translate': False,
                'type': 'premium'
            })
        if OperationalEntitiesConfig[3]['enabled'] and OperationalEntitiesGetterService.get_list(user, level=3).count() > 0:
            entities.append({
                'endpoint': 'entities.list_entities',
                'kwargs': {'level': 3},
                'micon': OperationalEntitiesHelper.get_icon(3),
                'label': OperationalEntitiesConfig[3]['names'],
                'translate': False,
                'type': 'premium'
            })
        if OperationalEntitiesConfig[2]['enabled'] and OperationalEntitiesGetterService.get_list(user, level=2).count() > 0:
            entities.append({
                'endpoint': 'entities.list_entities',
                'kwargs': {'level': 2},
                'micon': OperationalEntitiesHelper.get_icon(2),
                'label': OperationalEntitiesConfig[2]['names'],
                'translate': False,
            })
        if OperationalEntitiesConfig[1]['enabled'] and OperationalEntitiesGetterService.get_list(user, level=1).count() > 0:
            entities.append({
                'endpoint': 'entities.list_entities',
                'kwargs': {'level': 1},
                'micon': OperationalEntitiesHelper.get_icon(1),
                'label': OperationalEntitiesConfig[1]['names'],
                'translate': False
            })
        entities.append({
            'endpoint': 'entities.list_entities',
            'kwargs': {'level': 0},
            'micon': OperationalEntitiesHelper.get_icon(0),
            'label': OperationalEntitiesConfig[0]['names'],
            'translate': False
        })
        return entities

    @classmethod
    def get_menu(cls, user, filtered=True):
        all_menus = {
            'home': {
                'label': 'Home',
                'icon': 'home',
                'endpoint': 'overview.display_overview',
            },
            'tasks':{
                'label': 'Tasks',
                'icon': 'tasks',
                'permissions': ['ViewAssignedTasks', 'ViewTasks'],
                'endpoint' : 'task_manager.list_tasks',
                'notifications' : 'tasks',
                'enterprise': True
            },
            'leads': {
                'label': 'Sales',
                'icon': 'sales',
                'children': [{
                    'endpoint': 'leads.list_lead',
                    'permissions': ['ViewCreatedLeads', 'ViewLeads'],
                    'micon': 'gps_fixed',
                    'label': 'Leads',
                    'notifications': 'leads'
                }, {
                    'endpoint': 'lead_generator.list_lead_generator',
                    'permissions': 'ViewLeadGenerators',
                    'icon': 'generator',
                    'label': 'Generators'
                }, {
                    'endpoint': 'contract.list_addons',
                    'permissions': 'ConfigurePaymentManagementAdmin',
                    'icon': 'addon_offer',
                    'label': 'Add-Ons',
                    'notifications': 'addons',
                    'type': 'premium'
                }, {
                    'endpoint': 'sales_dashboard.sales_dashboard_view',
                    'permissions': 'ViewDashboards',
                    'icon': 'stats',
                    'label': 'Dashboard'
                }]
            },
            'clients': {
                'label': 'Clients',
                'icon': 'client',
                'children': [{
                    'endpoint': 'contract.list_contracts',
                    'permissions': 'ViewClients',
                    'icon': 'contract',
                    'label': 'Contracts',
                }, {
                    'endpoint': 'client.list_client',
                    'permissions': 'ViewClients',
                    'icon': 'client',
                    'label': 'Clients',
                }, {
                    'endpoint': 'contract.view_contract_dashboard',
                    'permissions': 'ViewDashboards',
                    'icon': 'stats',
                    'label': 'Dashboard',
                }, {
                    'endpoint': 'client.view_clients_demographics_dashboard',
                    'permissions': 'ViewDashboards',
                    'icon': 'stats',
                    'label': 'Demographics',
                }]
            },
            'reports': {
                'label': 'After-Sales',
                'icon': 'service',
                'enterprise': True,
                'children': [{
                    'endpoint': 'interaction_report.list_interaction_report',
                    'permissions': 'ViewInteractions',
                    'icon': 'interaction',
                    'label': 'Interactions',
                    'type': 'premium',
                    'enterprise': True
                }, {
                    'endpoint': 'issue.list_issue',
                    'permissions': 'ViewIssues',
                    'icon': 'issue',
                    'label': 'Issues',
                    'notifications': 'issues',
                    'type': 'premium',
                    'enterprise': True
                }, {
                    'endpoint': 'interaction_report.customer_support_dashboard',
                    'permissions': 'ViewInteractions',
                    'icon': 'stats',
                    'label': 'Dashboard',
                    'type': 'premium',
                    'enterprise': True
                }]
            },
            'management': {
                'label': 'Management',
                'icon': 'management',
                'children': [{
                    'endpoint': 'user.list_users',
                    'permissions': 'ViewUsers',
                    'icon': 'user',
                    'label': 'Users',
                    'type': 'premium'
                }, {
                    'endpoint': 'permissions.list_roles',
                    'icon': 'permission',
                    'label': 'Roles',
                    'type': 'premium',
                    'permissions': 'ViewRoles'
                }, {'divider': True}, {
                    'endpoint': 'portfolios.list_portfolios',
                    'permissions': 'ViewPortfolios',
                    'icon': 'portfolios',
                    'label': 'Portfolios'
                }, {'divider': True}] + ([{
                    'endpoint': 'entities.list_client_groups',
                    'permissions': ['AddClientGroups', 'EditClientGroups', 'DeleteClientGroups'],
                    'micon': 'groups',
                    'label': 'Client Groups'
                }, {'divider': True}] if (ClientGroupGetterService.get_list(user).count() > 0 or user.can_access('AddClientGroups')) and SettingsService.get_setting('FeatureToggles').get('ClientGroup') else []) + cls.get_operational_entities_menu(user)
            },
            'accounting': {
                'label': 'Accounting',
                'icon': 'accounting',
                'children': [{
                    'endpoint': 'payment.list_payment',
                    'permissions': ['ViewPayments', 'ViewOrphanedPayments', 'AddPayments'],
                    'icon': 'payment',
                    'label': 'Payments'
                }, {
                    'endpoint': 'reversed_payment.list_all',
                    'permissions': 'ViewReversedPayments',
                    'icon': 'reversal',
                    'label': 'Reversals',
                }, {
                    'endpoint': 'expense.list_expense',
                    'permissions': 'ViewExpenses',
                    'icon': 'expense',
                    'label': 'Expenses',
                    'type': 'premium'
                }, {
                    'endpoint': 'account.payments_dashboard',
                    'permissions': 'ViewGlobalDashboards',
                    'icon': 'stats',
                    'label': 'Dashboard'
                }, {'divider': True}, {
                    'endpoint': 'historical_data.gogla_dashboard',
                    'permissions': 'GoglaDashboards',
                    'icon': 'stats',
                    'label': 'GOGLA'
                }]
            },
            'inventory': {
                'label': 'Inventory',
                'icon': 'inventory',
                'children': [{
                    'endpoint': 'stock.stock_list',
                    'permissions': ['InStockViewStock', 'WithUsersViewStock', 'WithMeViewStock',
                                    'WithClientsViewStock', 'OrphanedViewStock'],
                    'icon': 'stock',
                    'label': 'Stock Items',
                    'type': 'premium'
                }, {
                    'endpoint': 'stock.stock_count',
                    'permissions': ['ManageQuantityViewStock'],
                    'icon': 'stock',
                    'label': 'Stock Count',
                    'type': 'premium'
                }, {
                    'endpoint': 'stock.stock_movements',
                    'permissions': ['InStockViewStock', 'WithUsersViewStock', 'WithMeViewStock',
                                    'WithClientsViewStock', 'OrphanedViewStock'],
                    'micon': 'compare_arrows',
                    'label': 'Stock Movements',
                    'type': 'premium'
                }]
            },
            'menu': {
                'label': 'Admin',
                'class': 'more-menu',
                'icon': 'admin',
                'children': [{
                    'endpoint': 'admin.admin',
                    'permissions': 'ViewSettingsInterfaceAdmin',
                    'icon': 'admin_specific',
                    'label': 'Admin'
                },{
                    'endpoint': 'admin.settings_menu',
                    'permissions': 'ViewSettingsInterfaceAdmin',
                    'icon': 'settings',
                    'label': 'Settings'
                }, {
                    'endpoint': 'admin.go_to_data_tool',
                    'target': '_blank',
                    'permissions': 'ViewGlobalDashboards',
                    'micon': 'insights',
                    'label': 'Dashboard Editor',
                    'type': 'premium',
                    'enterprise': True
                }, {
                    'endpoint': 'message.list_message',
                    'permissions': 'ViewMessages',
                    'micon': 'chat',
                    'label': 'Messages'
                }, {
                    'endpoint': 'mentor_request.list_request',
                    'permissions': 'ViewActions',
                    'micon': 'archive',
                    'label': 'Requests'
                }]
            }
        }
        # We add the custom menus
        ENTERPRISE_MODE = config.ENABLE_ENTERPRISE_FEATURES
        if ENTERPRISE_MODE:
            from app_builder_system.user_journey_editor.services.user_journey_service import UserJourneyService
            user_journeys_with_menu = UserJourneyService.get_list(user, has_menu=True)
            for uj in user_journeys_with_menu:
                version = uj.get_version_for_user(user)
                if version:
                    url = '/user_journey_editor/'+uj.slug
                    menu_details = {
                        'url': url,
                        'micon': version.userjourney.icon,
                        'label': version.userjourney.name,
                        'permissions':'RunUserJourney',
                        'translate': False,
                        'child_type': 'user_journey',
                        'id': version.id,
                        'slug': uj.slug
                    }
                    all_menus[uj.menu]['children'].insert(0, menu_details)
        
        # We add custom dashboard menus
        custom_dashboard_menus = SettingsService.get_setting('CustomDashboardsSideMenuSetting')
        if custom_dashboard_menus:
            for _, custom_dashboard in custom_dashboard_menus.items():
                url = '/overview/custom/generic/'+custom_dashboard.get('id')
                menu_details = {
                    'url': url,
                    'micon': custom_dashboard.get('button_icon'),
                    'label': custom_dashboard.get('button_name'),
                    'translate': False,
                    'child_type': 'custom_dashboard',
                    'id': custom_dashboard.get('id')
                }
                all_menus[custom_dashboard.get('menu')]['children'].insert(0, menu_details)

        # We Order user journey and custom dashboard
        all_menus = cls.get_ordered_menu(all_menus)
        side_menu_settings = SettingsService.get_setting('sideMenuSettings')
        

        # We remove any menu that is empty due to user permissions or disabled in the side menu settings
        clean_menus = copy.deepcopy(all_menus)
        if not ENTERPRISE_MODE:
            # Remove non-enterprise menus and children when enterprise mode is disabled
            for key, menu in list(all_menus.items()):
                if menu.get('enterprise'):
                    # Remove the whole menu entry by its key
                    clean_menus.pop(key, None)
                    continue
                # Filter out enterprise children directly from clean_menus
                if key in clean_menus and 'children' in clean_menus[key]:
                    clean_menus[key]['children'] = [
                        child for child in clean_menus[key]['children']
                        if not child.get('enterprise')
                    ]
        if (SettingsService.get_setting('PlatformType') == 'features-package' and not SettingsService.get_setting('FeatureToggles').get('TaskSystem', False)):
            if 'tasks' in clean_menus:
                del clean_menus['tasks']
        
        # Remove Add-Ons menu if neither ONE-OFF PAYMENTS nor CREDIT & SUBSCRIPTION PAYMENTS is enabled
        feature_toggles = SettingsService.get_setting('FeatureToggles')
        has_addon_contracts = feature_toggles.get('LumpSumContracts', False) or feature_toggles.get('LoanAndSubscriptionContracts', False)
        if not has_addon_contracts and 'leads' in clean_menus:
            clean_menus['leads']['children'] = [child for child in clean_menus['leads']['children'] if child.get('endpoint') != 'contract.list_addons']
        
        if filtered:
            for key, value in all_menus.items():
                all_menu_permissions = value.get('permissions', [])
                # Filter children directly from clean_menus instead of trying to remove by object identity
                if key in clean_menus and 'children' in clean_menus[key]:
                    clean_menus[key]['children'] = [
                        child for child in clean_menus[key]['children']
                        if not (
                            (child.get('permissions') and not user.can_access_in_any(child.get('permissions'))) or
                            side_menu_settings.get(key, {}).get("children", {}).get(child.get("label"), {}).get("enabled") == False
                        )
                    ]
                if key in clean_menus:
                    if len(clean_menus[key].get('children', [])) == 0 and not (clean_menus[key].get('url') or clean_menus[key].get('endpoint')):
                        del clean_menus[key]
                if key in clean_menus:
                    if (all_menu_permissions and not user.can_access_in_any(all_menu_permissions)) or side_menu_settings.get(key, {}).get("enabled") == False:
                        if key in clean_menus:
                            del clean_menus[key]
        return clean_menus
    
    @classmethod
    def get_ordered_menu(cls, all_menus):
        sortable_child_types = ['user_journey', 'custom_dashboard']
        menu_order = SettingsService.get_setting('sideMenuSettings')

        if not menu_order:
            return all_menus
        
        for menu_item, menu in all_menus.items():
            children = menu.get('children')
            order = menu_order.get(menu_item, {})

            if not children or not order:
                continue

            filtered_out_children = [c for c in children if c.get('child_type', '') not in sortable_child_types]
            child_map = {c.get('label'): c for c in children if c.get('child_type', '') in sortable_child_types}
            ujs = []
            for k, c in order.get('children', {}).items():
                if c.get('child_type', '') in ['user_journey'] and k in child_map:
                    ujs.append(child_map[k])
            cds = []
            for k, c in order.get('children', {}).items():
                if c.get('child_type', '') in ['custom_dashboard'] and k in child_map:
                    cds.append(child_map[k])

            ordered_children = ujs + filtered_out_children + cds
            all_menus[menu_item]['children'] = ordered_children

        return all_menus

    

    @classmethod
    @db_session
    def remove_custom_side_menu(cls, menu_item, child_label, child_type, slug):
        try:
            side_menu_settings = SettingsService.get_setting('sideMenuSettings') or {}
            if menu_item in side_menu_settings and side_menu_settings[menu_item].get('children'):
                children = side_menu_settings[menu_item]['children']
                if child_label in children:
                    del children[child_label]
                SettingsService.set_setting('sideMenuSettings', side_menu_settings)

            if child_type == 'user_journey' and config.ENABLE_ENTERPRISE_FEATURES:
                from app_builder_system.user_journey_editor.models.models import UserJourney
                journey = UserJourney.get(slug=slug) if slug else None
                if not journey and child_label:
                    journey = UserJourney.select(lambda uj: uj.name == child_label and uj.menu == menu_item).first()
                if journey:
                    journey.menu = ''
                    flush()

            elif child_type == 'custom_dashboard':
                custom_settings = SettingsService.get_setting('CustomDashboardsSideMenuSetting') or {}
                if child_label in custom_settings:
                    del custom_settings[child_label]
                SettingsService.set_setting('CustomDashboardsSideMenuSetting', custom_settings)

            return {'success': True, 'message': 'Custom side menu removed successfully'}
        except Exception as e:
            raise Error(f'Error removing custom side menu: {e}')
  