from pony.orm import Required, composite_key, Optional, db_session
from constants import CUSTOMISABLE_MSGS_INFO
from core_system.core_entities import db
from shared.services.language_service import LanguageService
from shared.api_helpers.model_definition_base import ModelDefinitionMixin



class CustomMessage(db.Entity, ModelDefinitionMixin):
    key = Required(str)
    template = Optional(str)
    language = Required(str)
    composite_key(key, language)

    @classmethod
    @db_session
    def get_model_definition(cls, op, **kwargs):
        languages = LanguageService.get_client_sms_language_dict()
        return {
            "properties": {
                'key': {
                    "type": "string",
                    "enum": list(CUSTOMISABLE_MSGS_INFO.keys()),
                    "example": "PAYMENT_RECEIVED",
                    "value": lambda o: o.key,
                    "description": "This is the Key of the custom message."
                },
                'language': {
                    "type": "string",
                    "enum": list(languages.keys()),
                    "example": "EN",
                    "value": lambda o: o.language,
                    "description": "This is the language code of the custom message."
                },
                'template': {
                    "type": "string",
                    "example": "Thank you for your payment of {amount} {currency_sym}.",
                    "value": lambda o: o.template,
                    "description": "This is the template of the custom message, includes vairables in curly braces ({ and })."
                }
            },
            "create_required": ["key", "language", "template"],
            "create_allowed": [],
            "create_forbidden": [],
            "edit_required": [],
            "edit_allowed": [],
            "view_required": [],
            "view_allowed": None
        }


