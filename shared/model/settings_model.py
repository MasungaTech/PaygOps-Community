from pony.orm import Required, Optional
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from core_system.core_entities import db
from datetime import time


class SettingList:

    settings = None
    setting_list = {}

    def __init__(self, settings):
        from shared.services.settings_service import SettingsService
        self.setting_list = {}
        self.settings = settings
        for s in settings:
            self.setting_list[s.key] = SettingsService.get_setting(s.key)
        self.setting_list = {key: str(val) if isinstance(val, time) else val for key, val in self.setting_list.items()}

    def get_serialized_object(self, **kwargs):
        return self.setting_list

    def parse_parameters(self, **kwargs):
        return {}

    def order_by(self, arg, **kwargs):
        return self.setting_list



class Settings(db.Entity, ModelDefinitionMixin):

    key = Required(str, unique=True)
    value = Optional(str)

    def get_serialized_object(self, **kwargs):
        from shared.services.settings_service import SettingsService
        return {
            'name': self.key,
            'value': SettingsService.get_setting(self.key)
        }

    @classmethod
    def get_model_definition(cls, op=None, **kwargs):
        return {
            'properties': {
                "name": {
                    "type": "string",
                    "example": "CurrencySymbol",
                    "description": "The name of the setting",
                    "value": lambda o: o.key
                },
                "value": {
                    "example": "TZS",
                    "description": "The value of the setting. It can be JSON objects in some cases or even empty. ",
                    "value": lambda o: o.value
                },
            },
            'view_required': [],
            'view_allowed': [],
            'edit_required': [],
            'edit_allowed': ["value"],
            'create_allowed': [],
            'create_required': []
        }
    