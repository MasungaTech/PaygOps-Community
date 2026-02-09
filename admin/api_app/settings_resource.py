from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.model.settings_model import Settings
from shared.services.settings_service import SettingsService


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
