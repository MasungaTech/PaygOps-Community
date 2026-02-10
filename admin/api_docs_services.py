import config
from datetime import datetime
from core_system.core_entities import db
from payg_loan_system.offers.models import OfferType
from payg_loan_system.transaction_requests.services.transaction_service import CONTRACT_REFERENCE_SCHEMA, DEVICE_SERIAL_SCHEMA
from jinja2 import Template
import os

if config.ENABLE_ENTERPRISE_FEATURES:
    from after_sales_system.interaction_system.model.interaction_report_model import InteractionMethod


ID_SCHEMA = {
    "type": "integer",
    "example": 123
}

NAME_SCHEMA = {
    "type": "string",
    "example": "First Name"
}

SURNAME_SCHEMA = {
    "type": "string",
    "example": "Surname",
}

CLIENT_BASE = { # the hook should send a client shcema as in the rest of the api
    'client_id': ID_SCHEMA,
    'client_name': NAME_SCHEMA,
    'client_surname': SURNAME_SCHEMA,
    'contract_reference': {
        "type": "string",
        "example": "C00001"
    },
    'acting_user_id': ID_SCHEMA
}

SMS_SCHEMA = { #should be in the model
    'uuid': {
        "type": "string",
        "format": "uuid",
        "example": "xxxxxxx-yyyyyyy-zzzzzzz"
    },
    'to_number': {
        "type": "string",
        "format": "phone",
        "example": "+25512341234",
    },
    'from_number': {
        "type": "string",
        "format": "phone",
        "example": "+25512341234",
    },
    'body': {
        "type": "string",
        "example": "Any text to be sent",
    },
    'sent_datetime': {
        "description": "This is the date and time at which the SMS was sent.",
        "type": "string",
        "format": "date-time",
        "example": datetime(2020, 6, 15).isoformat(),
    }
}

if config.ENABLE_ENTERPRISE_FEATURES:
    INTERACTION_SCHEMA = { #should be in the model
        'id': ID_SCHEMA,
        'client_id': ID_SCHEMA,
        'client_name': NAME_SCHEMA,
        'user_id': ID_SCHEMA,
        'user_name': NAME_SCHEMA,
        'date': {
            "type": "string",
            "format": "date-time",
            "example": datetime.now().isoformat(),
        },
        'main_topic': {
            "type": "string",
            "example": "MyInteractionTopic",
        },
        'method': {
            "type": "string",
            "enum": [InteractionMethod.to_human(m) for m in InteractionMethod.to_list()],
            "example": "Visit",
        },
        'client_initiated': {
            "type": "boolean",
            "example": False
        }
    }
else:
    INTERACTION_SCHEMA = {}

SWAP_SCHEMA = {
    'client_id': ID_SCHEMA,
    'client_name': NAME_SCHEMA,
    'client_surname': SURNAME_SCHEMA,
    'contract_reference': CONTRACT_REFERENCE_SCHEMA,
    'old_device_serial_number': {
        "type": "string",
        "example": "ABC-1234"
    },
    'new_device_serial_number': {
        "type": "string",
        "example": "CBA-4321"
    },
    'acting_user_id': ID_SCHEMA
}

COMMAND_BASE = {
    'command': {
        "type": "string",
        "example": "NOT_KNOWN_COMMAND"
    },
    'variables': {
        "type": "array",
        "items": {
            "type": "string"
        },
        "example": ["123", "TEXT"]
    },
    'from_number': {
        "type": "string",
        "format": "phone",
        "example": "+25512341234",
    },
}

USER_COMMAND = {
    'user_id': ID_SCHEMA,
    'user_name': NAME_SCHEMA,
    'user_surname': SURNAME_SCHEMA
}

CLIENT_COMMAND = {
    'client_id': ID_SCHEMA,
    'client_name': NAME_SCHEMA,
    'client_surname': SURNAME_SCHEMA
}

UNDO_DEFAULT_SCHEMA = {
    'client_id': ID_SCHEMA,
    'client_name': NAME_SCHEMA,
    'client_surname': SURNAME_SCHEMA,
    'contract_reference': {
        "type": "string",
        "example": "C0001"
    },
    'device_serial_number': {
        "type": "string",
        "example": "ABC-1234"
    },
    'offer_code': {
        "type": "string",
        "example": "CODE1"
    },
    'offer_type': {
        "type": "string",
        "enum": OfferType.to_list(),
        "example": "Loan"
    },
    'acting_user_id': ID_SCHEMA
}

DEFAULT_SCHEMA = {
    'client_id': ID_SCHEMA,
    'client_name': NAME_SCHEMA,
    'client_surname': SURNAME_SCHEMA,
    'contract_reference': CONTRACT_REFERENCE_SCHEMA,
    'acting_user_id': ID_SCHEMA
}

DELAY_GIVEN_SCHEMA = {
    'client_id': ID_SCHEMA,
    'name': NAME_SCHEMA,
    'surname': SURNAME_SCHEMA,
    'contract_reference': CONTRACT_REFERENCE_SCHEMA,
    'device_serial_number': DEVICE_SERIAL_SCHEMA,
    'delayed_days': {
        "type": "integer",
        "example": 3
    },
    'contract_event_id': {
        "type": "integer",
        "example": 21
    },
    'acting_user_id': ID_SCHEMA,
}

DISCOUNT_GIVEN_SCHEMA = {
    'client_id': ID_SCHEMA,
    'name': NAME_SCHEMA,
    'surname': SURNAME_SCHEMA,
    'contract_reference': CONTRACT_REFERENCE_SCHEMA,
    'device_serial_number': DEVICE_SERIAL_SCHEMA,
    'unit_name': {
        "type": "string",
        "example": "KWh"
    },
    'discounted_units': {
        "type": "integer",
        "example": 21
    },
    'discounted_days': {
        "type": "integer",
        "example": 3
    },
    'discounted_amount': {
        "type": "number",
        "example": 322.23
    },
    'contract_event_id': {
        "type": "integer",
        "example": 21
    },
    'acting_user_id': ID_SCHEMA,
}

OFFER_CHANGED_SCHEMA = {
    'client_id': ID_SCHEMA,
    'name': NAME_SCHEMA,
    'surname': SURNAME_SCHEMA,
    'contract_reference': CONTRACT_REFERENCE_SCHEMA,
    'device_serial_number': DEVICE_SERIAL_SCHEMA,
    'delayed_days': {
        "type": "integer",
        "example": 3
    },
    'old_offer_code': {
        "type": "string",
        "example": "TX1"
    },
    'new_offer_code': {
        "type": "string",
        "example": "TX2"
    },
    'contract_event_id': {
        "type": "integer",
        "example": 21
    },
    'acting_user_id': ID_SCHEMA,
}

CONTRACT_PAUSE_RESUME_SCHEMA = {
    'client_id': ID_SCHEMA,
    'name': NAME_SCHEMA,
    'surname': SURNAME_SCHEMA,
    'contract_reference': CONTRACT_REFERENCE_SCHEMA,
    'acting_user_id': ID_SCHEMA,
    'contract_event_id': {
        "type": "integer",
        "example": 21
    },
    'device_serial_number': DEVICE_SERIAL_SCHEMA,
}

ADDON_PLANNED_DELIVERY_DATE_CHANGE_SCHEMA = {
    'lead_id': ID_SCHEMA,
    'contract_reference': CONTRACT_REFERENCE_SCHEMA,
    'acting_user_id': ID_SCHEMA,
    'contract_event_id': {
        "type": "integer",
        "example": 21
    },
    'device_serial_number': DEVICE_SERIAL_SCHEMA,
    'add_on_reference': {
        "type": "string",
        "example": "TX1"
    },
    'old_planned_delivery_date': {
        "type": "string",
        "format": "date",
        "example": datetime.now().isoformat(),
    },
    'new_planned_delivery_date': {
        "type": "string",
        "format": "date",
        "example": datetime.now().isoformat(),
    },
}


class APIDocsService:

    # Build MODELS dictionary conditionally based on enterprise features
    _base_models = {
        "lead_added": db.Lead,
        "lead_edited": db.Lead,
        "client_edited": db.Client,
        "new_payment": db.Payment,
        "new_contract_payment": db.Payment,
        "new_orphaned_payment": db.Payment,
        "new_lead_payment": db.Payment,
        "new_addon_payment": db.Payment,
        "new_user_payment": db.Payment,
        "contract_payment": db.ContractRepayment,
        "user_created": db.User,
        "user_edited": db.User,
        "new_stock_movement": db.StockMovement,
        "new_addon_offer": db.AddOnOffer,
        "new_reconciliation": db.ReconciledPayment,
        "new_addon_offer_version": db.AddOnOfferVersion,
        "new_addon": db.ContractAddOn,
        "addon_approved": db.ContractAddOn,
        "addon_delivered": db.ContractAddOn,
        "addon_undelivered": db.ContractAddOn,
        "addon_cancelled": db.ContractAddOn,
    }
    
    # Add enterprise models only if enterprise features are enabled
    if config.ENABLE_ENTERPRISE_FEATURES:
        _enterprise_models = {
            "new_issue": db.Issue,
            "issue_closed": db.Issue,
            "task_created": db.Task,
            "task_edited": db.Task,
        }
        MODELS = {**_base_models, **_enterprise_models}
    else:
        MODELS = _base_models.copy()

    @classmethod
    def generate_api_docs(cls, user=None):
        from shared.api_helpers.api_structure import API_STRUCTURE
        paths = {path: resource.docs_get_metadata(user) for resource, path in API_STRUCTURE.items() if getattr(resource, 'PUBLIC', False) and (not user or not getattr(resource, 'VIEW_DOCS_PERMISSION', False) or user.can_access_in_any(getattr(resource, 'VIEW_DOCS_PERMISSION'), for_api_docs=True))}
        with open('/crm/admin/web_app/templates/public_api_docs.json', 'r') as file:
            template_string = file.read()
        template = Template(template_string)
        template.environment.policies['json.dumps_kwargs'] = {'sort_keys': False}
        content = template.render(
            server=config.PAYG_API_URL+config.API_PREFIX,
            config=config,
            paths=paths,
            current_user=user,
            get_hook_data=cls.get_hook_data,
            get_available_features=cls.get_available_features,
        )
        return content

    @classmethod
    def get_hook_data(cls, hook, only_description=False):

        description = ""
        properties = {}
        schema = None

        if hook in cls.MODELS:
            schema = cls.MODELS[hook].get_model_schema()

        if hook == 'new_contract_payment':
            description = 'This is sent when a payment is received that is routed to a contract (whether or not it actually leads to a repayment)'

        if hook == 'contract_payment':
            description = 'This is sent when a repayment is created on a contract (it can be any type of repayment including discount)'

        if hook == 'client_registered':
            description = "Client Data"
            properties = CLIENT_BASE
            properties.update({
                'lead_id': {
                    "type": "integer",
                    "example": 123
                },
                'lead_generator_id': {
                    "type": "integer",
                    "example": 123
                },
                'device_serial_number': {
                    "type": "string",
                    "example": "ABC-123456"
                },
                'total_loan_value': {
                    "type": "number",
                    "format": "float",
                    "example": 100100.45
                },
                'offer_code': {
                    "type": "string",
                    "example": "MyCode"
                },
                'offer_type': {
                    "type": "string",
                    "example": "Loan"
                }
            })

        if hook == "client_deregistered":
            description = "Client Data"
            properties = CLIENT_BASE
        
        if hook == "contract_cancelled":
            description = "Client Data"
            properties = CLIENT_BASE
        
        if hook == "outgoing_message":
            description = "Message Data"
            properties = SMS_SCHEMA

        if hook == "new_interaction":
            description = "Interaction Data"
            properties = INTERACTION_SCHEMA

        if hook == "device_swapped":
            description = "Swap Data"
            properties = SWAP_SCHEMA

        if hook == "unknown_user_sms_command":
            description = "Command Data"
            USER_COMMAND.update(COMMAND_BASE)
            properties = USER_COMMAND

        if hook == "unknown_client_sms_command":
            description = "Command Data"
            CLIENT_COMMAND.update(COMMAND_BASE)
            properties = CLIENT_COMMAND

        if hook == "undo_contract_default":
            description = "Transaction Data"
            properties = UNDO_DEFAULT_SCHEMA

        if hook == "contract_defaulted":
            description = "Transaction Data"
            properties = DEFAULT_SCHEMA

        if hook == "delay_given":
            description = "Transaction Data"
            properties = DELAY_GIVEN_SCHEMA

        if hook == "discount_given":
            description = "Transaction Data"
            properties = DISCOUNT_GIVEN_SCHEMA

        if hook == "offer_changed":
            description = "Transaction Data"
            properties = OFFER_CHANGED_SCHEMA

        if hook == 'contract_paused':
            description = "Transaction Data"
            properties = CONTRACT_PAUSE_RESUME_SCHEMA

        if hook == 'contract_resumed':
            description = "Transaction Data"
            properties = CONTRACT_PAUSE_RESUME_SCHEMA
        
        if hook == 'addon_planned_delivery_date_change':
            description = "Addon Data"
            properties = ADDON_PLANNED_DELIVERY_DATE_CHANGE_SCHEMA

        if not schema:
            schema = {
                "type": "object",
                "description": description,
                "properties": properties
            }

        if only_description:
            return description
        
        schema['properties'].update({'webhook_sent_datetime': {
            "type": "string",
            "description": "The time at which the webhook was sent from PaygOps.",
            "format": "date-time",
            "example": datetime.now().isoformat()
        }})

        return schema

    @classmethod
    def get_available_features(cls, permissions):
        if not permissions:
            return
        keys_with_value = []
        for key, feature_values in config.FEATURE_FLAGS_CONFIG.items():
            if any(value in feature_values for value in permissions):
                keys_with_value.append(key)
        return [config.FEATURE_NAME_MAP.get(key,key) for key in keys_with_value]