from flask import request
from shared.api_helpers.documented_resource import DocumentedResource
from shared.api_helpers.server_helpers.jwt_and_schema_verification import verify
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.model.settings_model import Settings
from shared.services.settings_service import SettingsService
from shared.services.web_menu_service import WebMenuService
from shared.logger.loggers import Error
# from core_system.users.services.current_user_service import get_current_api_user
from pony.orm import db_session


class SettingsResource(BaseAPIResourceIndividual):

    GET_SERVICE = SettingsService
    EDIT_SERVICE = SettingsService
    GET_PERMISSION = 'ConfigureGeneralSettingsAdmin'
    EDIT_PERMISSION = 'ConfigureGeneralSettingsAdmin'
    OBJECT_NAME = 'Settings'
    MODEL = Settings
    TAG = 'Miscellaneous'
    ALLOWED_API_CALLER = ['post']
    ID_PARAM  = {
        "name": "name",
        "in": "path",
        "description": "The name of the setting",
        "required": True,
        "example": "CurrencySymbol",
        "schema": {
            "type": "string"
        }
    }

class SettingsResourceAll(BaseAPIResourceAll):
    PUBLIC = False

    ADD_SERVICE = SettingsService
    LIST_SERVICE = SettingsService
    ADD_PERMISSION = 'ConfigureGeneralSettingsAdmin'
    LIST_PERMISSION = 'SuperAdmin'
    OBJECT_NAME = 'Settings'
    MODEL = Settings
    USE_PARENT_MODEL = False
    TAG = 'Miscellaneous'




class RemoveCustomSideMenuResource(DocumentedResource):
    PUBLIC = False  # Skip API definition test (undocumented admin endpoint)

    @verify(permissions=['ConfigureSpecialSettingsAdmin'])
    @db_session
    def post(self):
        data = request.json or {}
        menu_item = data.get('menu_item')
        child_label = data.get('child_label')
        child_type = data.get('child_type')
        slug = data.get('slug')

        if not menu_item or not child_label or not child_type:
            return {'success': False, 'msg': 'Missing required fields: menu_item, child_label, child_type'}, 400

        if child_type not in ('user_journey', 'custom_dashboard'):
            return {'success': False, 'msg': 'Invalid child_type; must be user_journey or custom_dashboard'}, 400

        try:
            result = WebMenuService.remove_custom_side_menu(menu_item, child_label, child_type, slug)
            return result, 200
        except Error as e:
            return {'success': False, 'msg': str(e)}, 400
    