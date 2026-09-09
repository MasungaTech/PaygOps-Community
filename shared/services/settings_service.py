import json
import re
from datetime import datetime, time
from decimal import Decimal, DecimalException
from typing import Any
from string import Formatter
import dateutil
from jsonschema import validate
from pony import orm
from pony.orm import select
from werkzeug.exceptions import NotFound

import config
from constants import MAX_ENTITY_LEVEL
from core_system.operational_entities.models import OperationalEntity
from shared.logger.loggers import Error, LogAPI
from shared.model.settings_model import SettingList, Settings
from shared.services.base_getter_service import BaseGetterService
from shared.services.celery_queue_service import CeleryQueueService
from shared.services.logo_converter_service import LogoConverterService
from worker_app.tasks.postprocess_forced_billing_exchange_rate import \
    postprocess_forced_billing_exchange_rate
from worker_app.tasks.update_reminder_task_time import \
    run_update_payment_reminder_time

def device_api_settings_preprocessor(device_types):
    from payg_loan_system.devices.device_api.device_api_service import \
        DeviceAPIService
    from payg_loan_system.devices.device_api.device_api_errors import DeviceAPIError
    from payg_loan_system.devices.model.device import Device
    from payg_loan_system.offers.models import Offer

    types = list(select(d.type for d in Device if d.type != 'NPG'))
    offers = list(select(o.device_type for o in Offer if o.device_type not in ['NPG', '']))
    for device_type in device_types:
        if device_type in types:
            types.remove(device_type)
        if device_type in offers:
            offers.remove(device_type)
        try:
            device_types[device_type]['supported_units'] = DeviceAPIService.get_available_unit_types_for_device_type(device_type, device_types[device_type])
        except DeviceAPIError:
            # If API key is invalid or there's an error, mark the URL as invalid and continue
            url = device_types[device_type].get('device_api_url', '')
            if '<invalid>' not in url:
                device_types[device_type]['device_api_url'] = url + '<invalid>'
            # Keep existing supported_units if available, otherwise use empty dict
            if 'supported_units' not in device_types[device_type]:
                device_types[device_type]['supported_units'] = {}
        except Exception:
            # Catch any other unexpected errors and mark as invalid
            url = device_types[device_type].get('device_api_url', '')
            if '<invalid>' not in url:
                device_types[device_type]['device_api_url'] = url + '<invalid>'
            if 'supported_units' not in device_types[device_type]:
                device_types[device_type]['supported_units'] = {}
    if types:
        raise Error('Cannot delete or change name of device API configuration with existing devices')
    if offers:
        raise Error('Cannot delete or change name of device API configuration with existing offers')
    return device_types

ENTITY_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "minLength": 1
        },
        "names": {
            "type": "string",
            "minLength": 1
        },
        "enabled": {
            "type": "boolean"
        }
    },
    "required": ["name", "names", "enabled"],
    "additionalProperties": False,
}

def validate_regex_pattern(value):
    try:
        re.compile(value)
    except re.error:
        return False
    return True


def validate_device_apis(value):
    if 'new' in value:
        code = value['new']['device_api_code']
        value[code] = value['new']
        del value[code]['device_api_code']
        del value['new']
    return True

def validate_operational_entities_config(value):
    enabled = True
    i=0
    for level in value:
        if not enabled and level.get('enabled', True):
            raise Error('You cannot disabled middle levels, disable first the top ones')
        enabled = level.get('enabled', True)
        if not enabled and OperationalEntity.select(lambda oe: oe.level==i).count() != 1:
            raise Error('You cannot disable '+level['names']+' (level '+str(i)+'), because it has more than one entity. Merge them before disabling.')
        i += 1
    return True

def level_is_empty(level):
    from stock_management_system.models import StockItem
    from stock_management_system.quantity_stock_models import QuantityStockLocation
    quantity_locations = QuantityStockLocation.select(
        lambda qsl: qsl.operational_entity.level == level and qsl.total_quantity != 0
    ).exists()
    items = StockItem.select(lambda si: si.shop.level == level).exists()
    return not (quantity_locations or items)

def preprocess_operational_entities_inventory(value):
    if config.MIGRATE_MODE and not value:
        value = []
        conf = SettingsService.get_setting('OperationalEntities')
        for level_data in conf:
            value.append(level_data.get('enabled', True))
    return value

def validate_operational_entities_inventory(value):
    conf = SettingsService.get_setting('OperationalEntities')
    for level, enabled in enumerate(value):
        if enabled and not conf[level].get('enabled', True):
            raise Error('You cannot enable inventory for levels that are not enabled')
        if not enabled and not level_is_empty(level):
            raise Error(f'You cannot disable lavel {level+1} because there are stock items in entities at that level')
    return True


def validate_personal_info_settings(value):
    for prop, config in value.items():
        if not config.get('visible', True) and config.get('required', False):
            raise Error('You cannot hide required property '+prop)
    return True


def validate_custom_button_configuration(value):
    if not value:
        return True

    formatter = Formatter()
    allowed_variables_by_page = {
        page: {variable for variable, _ in variables}
        for page, variables in config.CUSTOM_BUTTON_VARIABLES_BY_PAGE.items()
    }
    # Backwards compatibility: these variables can be formatted for contracts even if not listed for users
    allowed_variables_by_page.setdefault('contract', set()).update({'contract_id', 'contract_phone_number'})

    for index, button in enumerate(value, start=1):
        if not isinstance(button, dict):
            raise Error('Invalid custom button configuration entry.')

        target_page = button.get('TargetPage')
        target_url = button.get('TargetUrl') or ''

        if not target_page or target_page not in allowed_variables_by_page or not target_url:
            continue

        allowed_variables = allowed_variables_by_page[target_page]
        button_name = button.get('CustomButtonName') or f'#{index}'

        for _, field_name, format_spec, conversion in formatter.parse(target_url):
            if not field_name:
                continue

            # Remove attribute/item accessors to get the root variable name.
            variable_name = re.split(r'[\.\[]', field_name, maxsplit=1)[0]

            if variable_name not in allowed_variables:
                raise Error(
                    f'Variable "{variable_name}" cannot be used on target page "{target_page}" '
                    f'for custom button "{button_name}".'
                )
    return True

def postprocess_personal_info_settings():
    setting = Settings.get(key='LeadInfoSettings')
    if setting:
        setting_raw = json.loads(setting.value)
        if setting_raw['birthdate']['default']:
            clean_date = dateutil.parser.parse(setting_raw['birthdate']['default']).replace(hour=12)
            setting_raw['birthdate']['default'] = clean_date.replace(tzinfo=None).isoformat()
            setting.value = json.dumps(setting_raw)
    return True

def postprocess_forced_exchange_rate():
    rate = Settings.get(key='ForcedCurrencyExchangeRate')
    if rate:
        CeleryQueueService.execute_task(postprocess_forced_billing_exchange_rate)
    return True


def reprocess_pending_payments_on_enable_reversed_downpayments():
    from worker_app.tasks.try_reconcile_pending_payments import \
    try_reconcile_pending_payments

    """Reprocess all pending payments when EnableContractPaymentsForReversedDownpayments is enabled"""
    setting_value = SettingsService.get_setting('EnableContractPaymentsForReversedDownpayments')
    if setting_value:
        # Trigger reconciliation of all pending payments for all contracts
        CeleryQueueService.execute_task(try_reconcile_pending_payments)
    return True


def postprocess_feature_toggles():
    # Clean up old snake_case keys and migrate to PascalCase
    featureToggles = SettingsService.get_setting('FeatureToggles')
    
    # Migration map: old_key -> new_key
    key_migrations = {
        'offtaking': 'OffTaking',
        'task_system': 'TaskSystem',
        'user_journey_editor': 'UserJourneyEditor',
        'custom_app_designer': 'CustomAppDesigner',
        'automations': 'Automations',
        'package_installer': 'PackageInstaller',
        'no_value_loan_contracts': 'NoValueLoanContracts',
        'paquita': 'Paquita'
    }
    
    # Migrate old keys to new keys if they exist
    for old_key, new_key in key_migrations.items():
        if old_key in featureToggles:
            # Only migrate if the new key doesn't exist or if old key is True
            if new_key not in featureToggles or featureToggles.get(old_key):
                featureToggles[new_key] = featureToggles.get(old_key)
            # Remove the old key
            del featureToggles[old_key]
    
    # Also clean up the old 'ClientGroup' key if it exists (should be 'ClientGroups')
    if 'ClientGroup' in featureToggles:
        if 'ClientGroups' not in featureToggles or featureToggles.get('ClientGroup'):
            featureToggles['ClientGroups'] = featureToggles.get('ClientGroup')
        del featureToggles['ClientGroup']
    
    # If payment management is disabled we provide only basic routing rules
    if not SettingsService.get_setting('FeatureToggles').get('PaymentManagement'):
        BASIC_ROUTING_RULES = {"1": {"routing_attribute": "memo", "matching_parameter": "contract_reference", "strict": True, "validity_check": "", "validity_check_mode": "FIND_MATCH", "prepend": "", "append": "", "ignore_prefix": False}}
        SettingsService.set_setting('FlexiblePaymentRouterSettings', BASIC_ROUTING_RULES)
    # If leads is disabled, we provide only basic statuses
    if not SettingsService.get_setting('FeatureToggles').get('SalesFeatures'):
        from sales_system.leads.models.lead_status import LeadStatus
        from sales_system.leads.models.status_category import StatusCategory
        # We delete unused statuses
        for status in LeadStatus.select().filter(lambda s: orm.count(s.leads) == 0):
            if LeadStatus.select(lambda s: s.category == status.category).count() > 1:
                status.delete()
            orm.flush()
        # We create a default status in each category if any
        for category in StatusCategory.to_list():
            if not LeadStatus.select().filter(lambda s: s.category == category):
                new_status = LeadStatus(
                    name=category,
                    order=0,
                    category=category
                )
    # Retrieve the settings
    infoSettings = SettingsService.get_setting('LeadInfoSettings')
    featureToggles = SettingsService.get_setting('FeatureToggles')
    # Check the 'ClientGroups' feature toggle and update 'client_group' accordingly
    if featureToggles.get('ClientGroups'):
        infoSettings['client_group']['visible'] = True
    else:
        infoSettings['client_group']['visible'] = False
    infoSettings['client_group']['required'] = False
    # mark personal information required setting to false if sales feature is disable:
    if not featureToggles.get('SalesFeatures'):
        infoSettings['portfolio']['required'] = False
        infoSettings['gps_coordinates']['required'] = False
        infoSettings['profile_picture']['required'] = False
        SettingsService.set_setting('CustomIdMandatory', False)

    # Save the updated settings
    SettingsService.set_setting('LeadInfoSettings', value=infoSettings)
    lum_sum_enabled = SettingsService.get_setting('FeatureToggles').get('LumpSumContracts')
    loan_enabled = SettingsService.get_setting('FeatureToggles').get('LoanAndSubscriptionContracts')
    if not lum_sum_enabled and not loan_enabled:
        from payg_loan_system.offers.models import Offer
        offer = Offer.get(code='TDO')
        offer.in_use_for_new_clients = True
        offer.in_use = True
    if not SettingsService.get_setting('FeatureToggles').get('SSO'):
        SettingsService.set_setting('disablePasswordLogin', False)
    if not SettingsService.get_setting('FeatureToggles').get('MobileSSO'):
        SettingsService.set_setting('disablePasswordLoginMobile', False)



def validate_disable_password_login(value):
    if not SettingsService.get_setting('FeatureToggles').get('SSO') and value:
        raise Error('You cannot disable password login without Single Sign-on Feature')
    return True

def validate_disable_password_login_mobile(value):
    if not SettingsService.get_setting('FeatureToggles').get('MobileSSO') and value:
        raise Error('You cannot disable password login without Single Sign-on Feature on mobile')
    return True

def validate_custom_id_mandatory(value):
    if not SettingsService.get_setting('FeatureToggles').get('SalesFeatures') and value:
        raise Error('You cannot make mandatory the custom ID without the Leads feature')
    return True


class SettingsService(BaseGetterService):

    schema = {
        'FlexiblePaymentRouterSettings': {
            'type': 'json',
            'default': config.ROUTING_CONFIG,
            'permission': 'ConfigurePaymentRouterAdmin',
            'validation': {
                'JSONschema': {
                    "type": "object",
                    "patternProperties": {
                        "^[1-9]\\d*$": {
                            "type": "object",
                            "properties": {
                                "routing_attribute": {
                                    "type": "string",
                                    "options": config.AVAILABLE_ROUTING_ATTRIBUTES
                                },
                                "matching_parameter": {
                                    "type": "string",
                                    "options": config.AVAILABLE_MATCHING_PARAMETERS
                                },
                                "strict": {
                                    "type": "boolean"
                                },
                                "ignore_prefix": {
                                    "type": "boolean"
                                },
                                "validity_check": {
                                    "type": "string"
                                },
                                "validity_check_mode": {
                                    "type": "string",
                                    "options": config.AVAILABLE_VALIDITY_CHECK_MODE
                                },
                                "prepend": {
                                    "type": "string"
                                },
                                "append": {
                                    "type": "string"
                                }
                            },
                            "required": ["routing_attribute", "matching_parameter"],
                            "additionalProperties": False,
                        }
                    },
                    "additionalProperties": False
                }
            }
        },
        'LeadInfoSettings': {
            'default':{
                "first_name": {
                    "visible": True,
                    "required": True,
                },
                "surname": {
                    "visible": True,
                    "required": True,
                },
                "birthdate": {
                    "visible": True,
                    "required": False,
                    "has_default": True,
                    "default": "1970-01-01T12:00:00"
                },
                "gender": {
                    "visible": True,
                    "required": False,
                },
                "gps_coordinates": {
                    "visible": True,
                    "required": False,
                },
                "phone_number": {
                    "visible": True,
                    "required": True,
                },
                "verbal_language": {
                    "visible": True,
                    "required": False,
                    "has_default": True,
                    "default": ''
                },
                "preferred_sms_language": {
                    "visible": True,
                    "required": False,
                    "has_default": True,
                    "default": config.default_language
                },
                "home_use": { 
                    "visible": True,
                    "required": False,
                    "has_default": True,
                    "default": False
                },
                "business_use": {
                    "visible": True,
                    "required": False,
                    "has_default": True,
                    "default": False
                },
                "profile_picture": {
                    "visible": True,
                    "required": False,
                },
                "get_gps_from_picture": {
                    "visible": True,
                    "required": False,
                },
                "reasons_for_not_buying": {
                    "visible": True,
                    "required": False,
                    "has_default": True,
                    "default": []
                },
                "status": {
                    "visible": True,
                    "required": True,
                    "has_default": True,
                    "default": ''
                },
                "comment_on_status": {
                    "visible": True,
                    "required": False,
                },
                "next_planned_contact": {
                    "visible": True,
                    "required": False,
                },
                "portfolio": {
                    "visible": True,
                    "required": False,
                },
                "client_group": {
                    "visible": True,
                    "required": False,
                }
            },
            'type': 'json',
            'permission': 'ConfigurePersonalInfoAdmin',
            'callback': postprocess_personal_info_settings,
            'validation': {
                'function': validate_personal_info_settings,
                'JSONschema': {
                    "type": "object",
                    "properties": {
                        "first_name": {
                            "type": "object",
                            "properties": {
                                "visible": {
                                    "type": "boolean"
                                },
                                "required": {
                                    "type": "boolean"
                                },
                            }
                        },
                        "surname": {
                            "type": "object",
                            "properties": {
                                "visible": {
                                    "type": "boolean"
                                },
                                "required": {
                                    "type": "boolean"
                                },
                            }
                        },
                        "birthdate": {
                            "type": "object",
                            "properties": {
                                "visible": {
                                    "type": "boolean"
                                },
                                "required": {
                                    "type": "boolean"
                                },
                                "has_default": {
                                    "type": "boolean"
                                },
                                "default": {
                                    "type": "string",
                                    "format": "date-time"
                                },
                            }
                        },
                        "gender": {
                            "type": "object",
                            "properties": {
                                "visible": {
                                    "type": "boolean"
                                },
                                "required": {
                                    "type": "boolean"
                                },
                            }
                        },
                        "gps_coordinates": {
                            "type": "object",
                            "properties": {
                                "visible": {
                                    "type": "boolean"
                                },
                                "required": {
                                    "type": "boolean"
                                },
                            }
                        },
                        "verbal_language": {
                            "type": "object",
                            "properties": {
                                "visible": {
                                    "type": "boolean"
                                },
                                "required": {
                                    "type": "boolean"
                                },
                                "has_default": {
                                    "type": "boolean"
                                },
                                "default": {
                                    "type": "string",
                                },
                            }
                        },
                        "preferred_sms_language": {
                            "type": "object",
                            "properties": {
                                "visible": {
                                    "type": "boolean"
                                },
                                "required": {
                                    "type": "boolean"
                                },
                                "has_default": {
                                    "type": "boolean"
                                },
                                "default": {
                                    "type": "string",
                                },
                            }
                        },
                        "home_use": {
                            "type": "object",
                            "properties": {
                                "visible": {
                                    "type": "boolean"
                                },
                                "required": {
                                    "type": "boolean"
                                },
                                "has_default": {
                                    "type": "boolean"
                                },
                                "default": {
                                    "type": "boolean",
                                },
                            }
                        },
                        "business_use": {
                            "type": "object",
                            "properties": {
                                "visible": {
                                    "type": "boolean"
                                },
                                "required": {
                                    "type": "boolean"
                                },
                                "has_default": {
                                    "type": "boolean"
                                },
                                "default": {
                                    "type": "boolean",
                                },
                            }
                        },
                        "profile_picture": {
                            "type": "object",
                            "properties": {
                                "visible": {
                                    "type": "boolean"
                                },
                                "required": {
                                    "type": "boolean"
                                },
                            }
                        },
                        "get_gps_from_picture": {
                            "type": "object",
                            "properties": {
                                "visible": {
                                    "type": "boolean"
                                },
                                "required": {
                                    "type": "boolean"
                                }
                            }
                        },
                        "reasons_for_not_buying": {
                            "type": "object",
                            "properties": {
                                "visible": {
                                    "type": "boolean"
                                },
                                "required": {
                                    "type": "boolean"
                                },
                                "has_default": {
                                    "type": "boolean"
                                },
                                "default": {
                                    "type": "array",
                                    "items": {
                                        "oneOf": [

                                            {
                                                "type": "integer",
                                                "enum": list(config.REASONS_FOR_NOT_BUYING.keys())
                                            }
                                        ],
                                    },                                
                                },
                            }
                        },
                        "status": {
                            "type": "object",
                            "properties": {
                                "visible": {
                                    "type": "boolean"
                                },
                                "required": {
                                    "type": "boolean"
                                },
                                "has_default": {
                                    "type": "boolean"
                                },
                                "default": {
                                    "oneOf": [
                                        {"type": "integer"},
                                        { "type": "string", "maxLength": 0},
                                    ]
                                },
                            }
                        },
                        "comment_on_status": {
                            "type": "object",
                            "properties": {
                                "visible": {
                                    "type": "boolean"
                                },
                                "required": {
                                    "type": "boolean"
                                },

                            }
                        },
                        "phone_number": {
                            "type": "object",
                            "properties": {
                                "visible": {
                                    "type": "boolean"
                                },
                                "required": {
                                    "type": "boolean"
                                },

                            }
                        },
                        "next_planned_contact": {
                            "type": "object",
                            "properties": {
                                "visible": {
                                    "type": "boolean"
                                },
                                "required": {
                                    "type": "boolean"
                                },
                                "has_default": {
                                    "type": "boolean"
                                },
                                "default": {
                                    "type": "string",
                                    "format": "date-time"
                                },
                            }
                        },
                         "portfolio": {
                            "type": "object",
                            "properties": {
                                "visible": {
                                    "type": "boolean"
                                },
                                "required": {
                                    "type": "boolean"
                                },

                            }
                        },
                        "client_group": {
                            "type": "object",
                            "properties": {
                                "visible": {
                                    "type": "boolean"
                                },
                                "required": {
                                    "type": "boolean"
                                },

                            }
                        }
                    },
                    "additionalProperties": False
                }
            }
        },
        'statusTransitionRestrictions': {
            'type': 'json',
            'default': {},
            'permission': 'ConfigureGeneralSettingsAdmin',
            'validation': {
                'JSONschema': {
                    "type": "object",
                    "patternProperties": {
                        "^[1-9]*[0-9]*$": {
                            "type": "array",
                            "uniqueItems": True,
                            "items": {
                                "type": "integer"
                            }
                        }
                    },
                    "additionalProperties": False
                }
            }
        },
        'customButtonConfiguration': {
            'type': 'json',
            'default': [],
            'permission': 'ConfigureGeneralSettingsAdmin',
            'validation': {
                'JSONschema': {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "CustomButtonName": {
                                "type": "string",
                            },
                            "CustomButtonIcon": {
                                "type": "string",
                            },
                            "TargetUrl": {
                                "type": "string",
                                "pattern": "^(http(s?):\/\/.+)?$"
                            },
                            "TargetPage": {
                                "type": "string",
                                "enum": ["client", "lead", "contract"]
                            },
                        },
                        "additionalProperties": False
                    }
                },
                'function': validate_custom_button_configuration
            }
        },
        'SendPaymentReminderMessages': {
            'type': 'boolean',
            'default': config.auto_send_payment_reminder_sms,
            'permission': 'ConfigureAutomatedMessagesAdmin',
        },
        'TimeSendingPaymentReminder': {
            'type': 'time',
            'default': time(config.sms_reminders_hour_of_day,config.sms_reminders_minute_of_day),
            'permission': 'ConfigureAutomatedMessagesAdmin',
            'callback': run_update_payment_reminder_time
        },
        'PaymentRemindersDaysBeforeExpiry': {
            'type': 'json',
            'default': config.sms_reminders_days_before_expiry,
            'permission': 'ConfigureAutomatedMessagesAdmin',
            'validation': {
                'JSONschema': {
                    "type": "array",
                    "uniqueItems": True,
                    "items": {
                        "type": "integer"
                    }
                }
            }
        },
        'AllowPayingLeadWithOwnedAccount': {
            'type': 'boolean',
            'default': True,
            'permission': 'ConfigurePaymentManagementAdmin'
        },
        'AutoLinkAccountWhenPayingDownpayment': {
            'type': 'boolean',
            'default': config.auto_link_lead_account_to_client,
            'permission': 'ConfigurePaymentManagementAdmin'
        },
        'AutoRegisterLeadWithDownpaymentAndDevice': {
            'type': 'boolean',
            'default': False,
            'permission': 'ConfigurePaymentManagementAdmin'
        },
        'MarkAddOnsNotDeliveredDefault': {
            'type': 'boolean',
            'default': False,
            'permission': 'ConfigurePaymentManagementAdmin'
        },
        'AutomaticRepaymentReversal': {
            'type': 'boolean',
            'default': False,
            'permission': 'ConfigurePaymentManagementAdmin'
        },
        'AutomaticPaymentReversal': {
            'type': 'boolean',
            'default': False,
            'permission': 'ConfigurePaymentManagementAdmin'
        },
        'OdysseyFinancingID': {
            'type': 'string',
            'default': '',
            'permission': 'ConfigurePaymentManagementAdmin'
        },
        'AutomaticAutoReconcile': {
            'type': 'boolean',
            'default': False,
            'permission': 'ConfigurePaymentManagementAdmin'
        },
        'AutomaticAutoReconcileWeek': {
            'type': 'boolean',
            'default': False,
            'permission': 'ConfigurePaymentManagementAdmin'
        },
        'AutomaticAddOnReconciliation': {
            'type': 'boolean',
            'default': False,
            'permission': 'ConfigurePaymentManagementAdmin'
        },
        'FeatureToggles': {
            'type': 'json',
            'default': {
                'SalesFeatures': True,
                'LumpSumContracts': True,
                'LoanAndSubscriptionContracts': True,
                'AfterSales': True,
                'Inventory': True,
                'ClientGroups':True,
                'SSO':True,
                'MobileSSO':True,
                'AddOnsConfiguration':True,
                'AuditLogs':True,
                'PaymentManagement':True,
                'AutomatedMessagesSMS':True,
                'OffTaking':False,
                'OfflineMobileApp':True,
                'EnableUserGuiding': False,
                'ApiAccess': True,
                'BulkActions': True,
                'PaygoDevices': True,
                'TaskSystem': True,
                'UserJourneyEditor': False,
                'CustomAppDesigner': False,
                'Automations': False,
                'PackageInstaller': False,
                'NoValueLoanContracts': False,
                'Paquita': False,
                'BillingAnalytics': False,
                'BillingPaygOpsSMS': False
            },
            'permission': 'SuperAdmin',
            'callback': postprocess_feature_toggles
        },
        'SyncEntityByDefaultForNewUsersInCharge': {
            'type': 'boolean',
            'default': False,
            'permission': 'ConfigureGeneralSettingsAdmin'
        },
        'AllowPendingPayments': {
            'type': 'boolean',
            'default': False,
            'permission': 'ConfigurePaymentManagementAdmin'
        },
        'AllowPaymentsFromPausedContractsAsPending': {
            'type': 'boolean',
            'default': True,
            'permission': 'ConfigurePaymentManagementAdmin'
        },
        'AutoReconcilePendingPayments': {
            'type': 'boolean',
            'default': False,
            'permission': 'ConfigurePaymentManagementAdmin'
        },
        'RequirePhonePersonalInformation': {
            'type': 'boolean',
            'default': True,
            'permission': 'ConfigureGeneralSettingsAdmin'
        },
        'CustomId': {
            'type': 'string',
            'default': '',
            'permission': 'ConfigureGeneralSettingsAdmin',
            'validation': {
                'regex': "^.{0,20}$"
            }
        },
        'CustomIdEnabled': {
            'type': 'boolean',
            'default': False,
            'permission': 'ConfigureGeneralSettingsAdmin'
        },
        'CustomIdMandatory': {
            'type': 'boolean',
            'default': False,
            'permission': 'ConfigureGeneralSettingsAdmin',
            'validation': {
                'function': validate_custom_id_mandatory
            }
        },
        'CustomIdFormat': {
            'type': 'string',
            'default': '',
            'permission': 'ConfigureGeneralSettingsAdmin',
            'validation': {
                "function": validate_regex_pattern }
        },
        'MaxRoundingDiscount': {
            'type': "decimal",
            'default': 0.1,
            'permission': 'ConfigurePaymentManagementAdmin'
        },
        'CashCollectionLimitEnabled': {
            'type': "boolean",
            'default': False,
            'permission': 'ConfigurePaymentManagementAdmin'
        },
        'CashCollectionLimit': {
            'type': "decimal",
            'default': 0,
            'permission': 'ConfigurePaymentManagementAdmin'
        },
        'CashCollectionPercentageWarning': {
            'type': "decimal",
            'default': 0,
            'permission': 'ConfigurePaymentManagementAdmin',
            'validation': {
                'min': 0,
                'max': 100
            }
        },
        'CashCollectionAmountWarning': {
            'type': "decimal",
            'default': 0,
            'permission': 'ConfigurePaymentManagementAdmin'
        },
        'EnableLimitOnPlannedDeliveryDate': {
            'type': "boolean",
            'default': False,
            'permission': 'ConfigurePaymentManagementAdmin'
        },
        'StressMode': {
            'type': "boolean",
            'default': False,
            'permission': 'ConfigureSpecialSettingsAdmin'
        },
        'ShowStressBanner': {
            'type': "boolean",
            'default': False,
            'permission': 'ConfigureSpecialSettingsAdmin'
        },
        'BeforeLimitOnPlannedDeliveryDate': {
            'type': "integer",
            'default': 0,
            'permission': 'ConfigurePaymentManagementAdmin'
        },
        'AfterLimitOnPlannedDeliveryDate': {
            'type': "integer",
            'default': 0,
            'permission': 'ConfigurePaymentManagementAdmin'
        },
        'TargetTimezone': {
            'type': 'string',
            'default': config.target_timezone,
            'permission': 'ConfigureLocalSettingsAdmin',
            'validation': {
                'options': config.AVAILABLE_TIMEZONES
            },
            'callback': run_update_payment_reminder_time
        },
        'CurrencySymbol': {
            'type': 'string',
            'default': config.MainCurrencySymbol,
            'permission': 'ConfigureLocalSettingsAdmin',
        },
        'CurrencyISOName': {
            'type': 'string',
            'default': config.MainCurrencyISOName,
            'permission': 'ConfigureLocalSettingsAdmin',
        },
        'ForcedCurrencyCode': {
            'type': 'string',
            'default': '',
            'permission': 'SuperAdmin',
        },
        'ForcedCurrencyExchangeRate': {
            'type': 'decimal',
            'default': 0,
            'permission': 'SuperAdmin',
            'callback': postprocess_forced_exchange_rate
        },
        'CountryName': {
            'type': 'string',
            'default': config.CountryName,
            'permission': 'ConfigureLocalSettingsAdmin',
        },
        'CountryDescriptor': {
            'type': 'string',
            'default': config.CountryDescriptor,
            'permission': 'ConfigureLocalSettingsAdmin',
        },
        'PhoneExtension': {
            'type': 'string',
            'default': config.PhoneExtension,
            'permission': 'ConfigureLocalSettingsAdmin',
            'validation': {
                "regex": '^([1-9][0-9]*)?$'
            }
        },
        'PhoneLength': {
            'type': 'integer',
            'default': config.PhoneLength,
            'permission': 'ConfigureLocalSettingsAdmin',
        },
        'PhoneLengthMin': {
            'type': 'integer',
            'default': config.PhoneLengthMin,
            'permission': 'ConfigureLocalSettingsAdmin',
        },
        'FirstDayOfWeek': {
            'type': 'integer',
            'default': config.first_day_of_week,
            'permission': 'ConfigureGeneralSettingsAdmin',
            'validation': {
                'options': config.DAYS_OF_WEEK.keys()
            }
        },
        'MessageRecipient': {
            'type': 'string',
            'default': 'PAYMENT_NUMBER',
            'permission': 'ConfigureAutomatedMessagesAdmin',
            'validation': {
                'options': config.MESSAGE_RECIPIENT_OPTIONS.keys()
            }
        },
        'OperationalEntities': {
            'type': 'json',
            'default': config.OPERATIONAL_ENTITIES_CONFIG,
            'permission': 'ConfigureOperationalEntitiesAdmin',
            'validation': {
                'function': validate_operational_entities_config,
                'JSONschema': {
                    "type": "array",
                    "maxItems": MAX_ENTITY_LEVEL+1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "minLength": 1
                            },
                            "names": {
                                "type": "string",
                                "minLength": 1
                            },
                            "enabled": {
                                "type": "boolean"
                            }
                        },
                        "required": ["name", "names"],
                        "additionalProperties": False,
                    },
                    "additionalItems": False
                }
            }
        },
        'OperationalEntitiesInventory': {
            'type': 'json',
            'default': [True, True, True, False, False],
            'permission': 'ConfigureOperationalEntitiesAdmin',
            'preprocess': preprocess_operational_entities_inventory,
            'validation': {
                'function': validate_operational_entities_inventory,
                'JSONschema': {
                    "type": "array",
                    "maxItems": MAX_ENTITY_LEVEL+1,
                    "items": {
                        "type": "boolean",
                    },
                    "additionalItems": False
                }
            }
        },
        'PlatformType': {
            'type': 'string',
            'default': 'new-premium',
            'permission': 'SuperAdmin',
            'validation': {
                'options': config.PLATFORM_TYPES.keys()
            }
        },
        'APIBannedUsers': {
            'type': 'string',
            'default': '',
            'permission': 'SuperAdmin',
        },
        'BannerMessage': {
            'type': 'string',
            'default': '',
            'permission': 'EditBannerAdmin',
        },
        'MobileBannerMessage': {
            'type': 'string',
            'default': '',
            'permission': 'EditBannerAdmin',
        },
        'StressModeBanner': {
            'type': 'string',
            'default': 'The platform can be slower than usual due to high load. Please avoid refreshing or pressing options multiple times',
            'permission': 'SuperAdmin',
        },
        'GatewaySendingEnabled': {
            'type': 'boolean',
            'default': config.gateway_delivery_enabled,
            'permission': 'SuperAdmin',
        },
        'GatewaySendingAsynchronous': {
            'type': 'boolean',
            'default': config.delayed_gateway_post,
            'permission': 'SuperAdmin',
        },
        'PlatformLogoPictureID': {
            'type': 'string',
            'default': '',
            'permission': 'ConfigureGeneralSettingsAdmin',
            'callback': LogoConverterService.convert_logo_from_platform_settings
        },
        'DefaultWebLanguage': {
            'type': 'string',
            'default': config.web_language,
            'permission': 'ConfigureLanguageSettingsAdmin',
            'validation': {
                'options': config.AVAILABLE_WEB_LANGUAGES.keys()
            }
        },
        'DefaultSMSUsersLanguage': {
            'type': 'string',
            'default': config.default_language,
            'permission': 'ConfigureLanguageSettingsAdmin',
            'validation': {
                'options': config.AVAILABLE_USERS_SMS_LANGUAGES
            }
        },
        'DefaultSMSClientsLanguage': {
            'type': 'string',
            'default': config.default_client_language,
            'permission': 'ConfigureLanguageSettingsAdmin',
            'validation': {
                'options': config.AVAILABLE_CLIENTS_SMS_LANGUAGES
            }
        },
        'CustomLanguageName': {
            'type': 'string',
            'default': '',
            'permission': 'ConfigureLanguageSettingsAdmin',
        },
        'OnlineTrainingUrl': {
            'type': 'string',
            'default': config.default_online_training_url,
            'permission': 'ConfigureLanguageSettingsAdmin',
        },
        'FallBackDeviceType': {
            'type': 'string',
            'default': config.default_fallback_device_type,
            'permission': 'ConfigureDeviceAPIAdmin'
        },
        'HidePrefixFallBackDeviceType': {
            'type': 'boolean',
            'default': config.default_hide_prefix_fallback_device_type,
            'permission': 'ConfigureDeviceAPIAdmin'
        },
        'NPGDeviceEnabled': {
            'type': 'boolean',
            'default': config.default_npg_device_enabled,
            'permission': 'ConfigureDeviceAPIAdmin'
        },
        'MetabaseURL': {
            'type': "string",
            'default': '',
            'permission': 'ConfigureDeviceAPIAdmin'
        },
        'MetabaseKey': {
            'type': "string",
            'default': '',
            'permission': 'ConfigureDeviceAPIAdmin'
        },
        'CustomDashboards': {
            'type': 'json',
            'default': {},
            'permission': 'ConfigureGeneralSettingsAdmin'
        },
        'CustomDashboardsSideMenuSetting': {
            'type': 'json',
            'default': {},
            'permission': 'ConfigureGeneralSettingsAdmin'
        },
        'AnalyticalDBUsers': {
            'type': 'json',
            'default': {},
            'permission': 'SuperAdmin'
        },
        'DefaultConflictResolution': {
            'type': 'string',
            'default': 'ASK',
            'validation': {
                'options': config.CONFLICT_RESOLUTION_OPTIONS
            },
            'permission': 'SuperAdmin'
        },
        'AllDeviceAPIS': {
            'type': 'json',
            'default': config.all_device_apis,
            'permission': 'SuperAdmin',
            'preprocess': device_api_settings_preprocessor,
            'validation': {
                'function': validate_device_apis,
                'JSONschema': {
                    "type": "object",
                    "patternProperties": {
                        "^[A-Z0-9]{2,4}$": {
                            "type": "object",
                            "properties": {
                                "device_api_code": {
                                    "type": "string"
                                },
                                "device_api_key": {
                                    "type": "string"
                                },
                                "device_api_url": {
                                    "type": "string",
                                    "format": "uri"
                                },
                                "device_api_type": {
                                    "type": "string",
                                    "enum": list(config.AVAILABLE_DEVICE_API_TYPES.keys())
                                },
                                "device_api_full_name": {
                                    "type": "string"
                                },
                                "device_api_version": {
                                    "type": "string",
                                    "enum": config.AVAILABLE_DEVICE_API_VERIONS
                                },
                                "offline_mode": {
                                    "type": "string",
                                    "enum": list(config.AVAILABLE_DEVICE_API_OFFLINE_SUPPORT.keys())
                                },
                                "device_pairing":{
                                    "type": "string",
                                    "enum": list(config.AVAILABLE_DEVICE_API_OFFLINE_SUPPORT.keys())
                                },
                                "supports_monitoring_data": {
                                    "type": "string",
                                    "enum": list(config.AVAILABLE_DEVICE_API_OFFLINE_SUPPORT.keys())
                                },
                                "supported_offer_type": {
                                    "type": "string",
                                    "enum": list(config.AVAILABLE_SUPPORTED_OFFER_TYPES.keys())
                                },
                                "supported_units": {
                                    "type": "object"
                                }
                            },
                            "required": ["device_api_key", "device_api_url", "device_api_type"],
                            "additionalProperties": False
                        }
                    },
                    "additionalProperties": False
                }
            }
        },
        'BillingConfig': {
            'type': 'json',
            'default': {
                "customer_id": None,
                "show_billing_portal": False,
                "tier0": False
            },
            'permission': 'SuperAdmin',
            'validation': {
                'JSONschema': {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "oneOf": [
                                {"type": "string"},
                                {"type": "null"},
                            ]
                        },
                        "show_billing_portal": {
                            "type": "boolean",
                        },
                        "tier0": {
                            "type": "boolean",
                        }
                    },
                    "additionalProperties": False
                }
            }
        },
        'AllowMultiplePersonsWithSamePhoneNumber': {
            'type': 'boolean',
            'default': False,
            'permission': 'ConfigureGeneralSettingsAdmin'
        },
        'AllowMultipleContracts': {
            'type': 'boolean',
            'default': False,
            'permission': 'ConfigureGeneralSettingsAdmin'
        },
        'LastForcedSyncTime': {
            "type": "datetime",
            'permission': 'SuperAdmin',
            'default': None
        },
        'SyncPortoliosToMobileApp': {
            'type': 'boolean',
            'default': True,
            'permission': 'SuperAdmin'
        },
        'enableLoginPIN': {
            'type': 'boolean',
            'default': True,
            'permission': 'ConfigureGeneralSettingsAdmin'
        },
        'enforceTwoFactorForAllUsers': {
            'type': 'boolean',
            'default': False,
            'permission': 'ConfigureGeneralSettingsAdmin'
        },
        'disablePasswordLogin': {
            'type': 'boolean',
            'default': False,
            'permission': 'ConfigureGeneralSettingsAdmin',
            'validation': {
                'function': validate_disable_password_login,
            }
        },
        'disablePasswordLoginMobile': {
            'type': 'boolean',
            'default': False,
            'permission': 'ConfigureGeneralSettingsAdmin',
            'validation': {
                'function': validate_disable_password_login_mobile,
            }
        },
        'enableAccountsMenu': {
            'type': 'boolean',
            'default': False,
            'permission': 'SuperAdmin'
        },
        'SessionLifetime': {
            'type': "integer",
            'default': 0,
            'permission': 'ConfigureGeneralSettingsAdmin'
        },
        'GpsSurfaceMeasurementUnit': {
            'type': "string",
            'validation': {
                'options': config.GPS_SURFACE_MEASUREMENT_UNITS.keys()
            },
            'default': config.default_gps_surface_measurement_unit,
            'permission': 'ConfigureGeneralSettingsAdmin'
        },
        'EnableContractPaymentsForReversedDownpayments': {
            'type': "boolean",
            'default': True,
            'permission': 'ConfigurePaymentManagementAdmin',
            'callback': reprocess_pending_payments_on_enable_reversed_downpayments
        },

        'EnableLateStatus': {
            'type': 'boolean',
            'default': False,
            'permission': 'CustomizePlatformAdmin'
        },
        'DaysLateForLateStatus': {
            'type': 'integer',
            'default': 0,
            'permission': 'CustomizePlatformAdmin'
        },
        'CustomMenusConfig': {
            'type': 'json',
            'permission': 'SuperAdmin',
            'default': {}
        },
        'AllowUsersToReceiveStock': {
            'type': 'boolean',
            'default': False,
            'permission': 'ConfigureGeneralSettingsAdmin'
        },
        'EnableStockMovementsOnMobileApp': {
            'type': 'boolean',
            'default': False,
            'permission': 'ConfigureGeneralSettingsAdmin'
        },
        'PersonalDetailsEditingRestrictions': {
            "type": "integer",
            "permission": "ConfigureGeneralSettingsAdmin",
            "default": 0
        },
        'mobileAppCustomizationCardSetting': {
            'type': 'json',
            'permission': 'ConfigureGeneralSettingsAdmin',
            'default': {
                "enabled": False,
                "mobile_app_name": "Solaris Mobile App",
                "app_store_description": "Solaris Mobile App",
                "primary_corporate_colour": "#000",
                "picture_id": "",
                "available_in_google_play_store": False,
                "available_in_apple_app_store": False,
            },
            'validation': {
                'JSONschema': {
                    "type": "object",
                    "properties": {
                        "enabled": {
                            "type": "boolean",
                            "default": False
                        },
                        "mobile_app_name": {
                            "type": "string",
                            "minLength": 1,
                            "default": "Solaris Mobile App"
                        },
                        "app_store_description": {
                            "type": "string",
                            "minLength": 1,
                            "default": "Solaris Mobile App"
                        },
                        "primary_corporate_colour": {
                            "type": "string",
                            "default": "#000"
                        },
                        "picture_id": {
                            "type": "string",
                            "default": ""
                        },
                        "available_in_google_play_store": {
                            "type": "boolean",
                            "default": False
                        },
                        "available_in_apple_app_store": {
                            "type": "boolean",
                            "default": False
                        }
                    },
                    "required": [
                        "mobile_app_name",
                        "app_store_description",
                        "primary_corporate_colour",
                        "available_in_google_play_store",
                        "available_in_apple_app_store"
                    ]
                }
            }
        },
        'app_menu': {
            'type': 'json',
            'default': [],
            'permission': 'ConfigureGeneralSettingsAdmin',
            'validation': {
                'JSONschema': {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "oneOf": [
                            {
                                "properties": {
                                    "type": { "const": "user_journey" },
                                    "user_journey": { "type": "number" }
                                },
                                "required": ["type", "user_journey"],
                                "additionalProperties": False
                            },
                            {
                                "properties": {
                                    "type": { "const": "management" },
                                    "management": {
                                        "type": "string",
                                        "enum": ["client_groups", "operational_entities_0"]
                                    }
                                },
                                "required": ["type", "management"],
                                "additionalProperties": False
                            },
                            {
                                "properties": {
                                    "type": { "const": "after_sales" },
                                    "after_sales": {
                                        "type": "string",
                                        "enum": ["interactions", "issues", "after_sales_dashboard"]
                                    }
                                },
                                "required": ["type", "after_sales"],
                                "additionalProperties": False
                            },
                            {
                                "properties": {
                                    "type": { "const": "sales" },
                                    "sales": {
                                        "type": "string",
                                        "enum": ["list_leads", "add_lead"]
                                    }
                                },
                                "required": ["type", "sales"],
                                "additionalProperties": False
                            },
                            {
                                "properties": {
                                    "type": { "const": "clients" },
                                    "clients": {
                                        "type": "string",
                                        "enum": ["list_clients"]
                                    }
                                },
                                "required": ["type", "clients"],
                                "additionalProperties": False
                            },
                            {
                                "properties": {
                                    "type": { "const": "inventory" },
                                    "inventory": {
                                        "type": "string",
                                        "enum": ["stock_movements", "stock_items"]
                                    }
                                },
                                "required": ["type", "inventory"],
                                "additionalProperties": False
                            }
                        ]
                    },
                    "additionalItems": False
                }
            }
        },
        'taskMenuSetting': {
            'type': 'json',
            'permission': 'ConfigureGeneralSettingsAdmin',
            'default': {
                "enabled": False
            },
            'validation': {
                'JSONschema': {
                    "type": "object",
                    "properties": {
                        "enabled": {
                            "type": "boolean",
                            "default": False
                        }
                    },
                    "required": [
                        "enabled"
                    ]
                }
            }
        },
        'sideMenuSettings': {
            'type': 'json',
            'default': {},
            'permission': 'ConfigureGeneralSettingsAdmin',
        },
        'OriginOfNonSerializedStockItems': {
        'type': 'json',
        'default': {
            'origin': 'user',  # Default value is 'User'
            'level': None  # Default is None when no level is selected
        },
        'permission': 'ConfigureGeneralSettingsAdmin',
        'validation': {
            'JSONschema': {
                "type": "object",
                "properties": {
                    "origin": {
                        "type": "string",
                        "default": "user",
                    },
                    "level": {
                        "oneOf": [
                            {
                                "type": "string",
                            },
                            {
                                "type": "null",  # Allow None (null)
                            }
                        ],
                        "default": None  # No level selected by default
                    },
                },
                "required": ["origin"],
                "additionalProperties": False,
                "dependencies": {}
            }
        }
    },
    'AutomationGlobalConfig': {
        'type': 'json',
        'default': '{}',
        'permission': 'EditAutomations',
        'validation': {
            'JSONschema': {
                "type": "object",
                "additionalProperties": True
            }
        }
    },
    'PaymentSendingGateways': {
        'type': 'json',
        'default': {},
        'permission': 'ConfigurePaymentManagementAdmin',
        'validation': {
            'JSONschema': {
                'type': 'object',
                'patternProperties': {
                    '^.+$': {  # match any key like "Mpesa-KE"
                        'type': 'object',
                        'properties': {
                            'display_name': {'type': 'string'},
                            'enabled': {'type': 'boolean'}
                        },
                        'required': ['display_name', 'enabled'],
                        'additionalProperties': False
                    }
                },
                'additionalProperties': False
            }
        }
    },
    'ContractDeviceRestrictions': {
        'type': 'string',
        'default': 'require_device',
        'permission': 'ConfigureSalesManagementAdmin',
        'validation': {
            'options': ['both', 'require_device', 'no_device']
        }
    }
}


    @classmethod
    def get_setting(cls, key, include_obsolete=False, setting=None):
        if key in cls.schema or include_obsolete:
            setting = Settings.get(key=key) if not setting else setting
            type = cls.schema[key]['type']
            if setting:
                return cls._get_type_compliant(setting.value, type)
            LogAPI.check_and_warn(not config.MIGRATE_MODE and not config.INSTALL_MODE, f'Setting missing in the database: "{key}"')
            return cls.schema[key]['default']
        raise Exception('INVALID SETTINGS KEY')

    @classmethod
    def set_setting(cls, key, value, user=None):
        if key in cls.schema:
            if not user or user.can_access(cls.schema[key]['permission']):
                type = cls.schema[key]['type']
                value = cls._get_type_compliant(value, type)
                rules = cls.schema[key].get('validation', {})
                if cls._check_validity(value, type, rules):
                    value = cls._execute_preprocess(cls.schema[key], value)
                    DBvalue = cls._get_DB_compliant(value, type)
                    setting = Settings.get(key=key)
                    if setting:
                        setting.value = DBvalue
                    else:
                        Settings(key=key, value=DBvalue)
                    cls._execute_callback(cls.schema[key])
                else:
                    raise Exception(f'Invalid value {value} for setting {key}')
            else:
                raise Exception('THE USER HAS NOT THE REQUIRED PERMISSIONS')
        else:
            raise Exception(f'INVALID SETTINGS KEY')

    @classmethod
    def _execute_callback(cls, schema_key):
        callback_function = schema_key.get('callback')
        if callback_function:
            callback_function()

    @classmethod
    def _execute_preprocess(cls, schema_key, value):
        return schema_key['preprocess'](value) if 'preprocess' in schema_key else value

    @classmethod
    def set_defaults(cls, override=False, remove_obsolete=True):
        for setting, schema in cls.schema.items():
            if override or not Settings.get(key=setting):
                try:
                    cls.set_setting(setting, schema['default'])
                except Exception as e:
                    LogAPI.FatalNoRequest(e)
        # Special case for feature toggles
        feature_toggles = cls.get_setting('FeatureToggles')
        feature_toggles_default = cls.schema.get('FeatureToggles').get('default')
        update_toggles = False
        for key, value in feature_toggles_default.items():
            if key not in feature_toggles:
                update_toggles = True
                feature_toggles[key] = value
        if update_toggles:
            cls.set_setting('FeatureToggles', feature_toggles)
        if remove_obsolete:
            for setting in Settings.select():
                if setting.key not in cls.schema:
                    setting.delete()

    @classmethod
    def user_allowed_to_edit(cls, user):
        for setting, schema in cls.schema.items():
            if user.can_access(schema['permission']):
                return True
        return False

    @classmethod
    def _get_type_compliant(cls, value, type):
        if type == 'boolean':
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                if value.lower() in ['true', 'yes', '1']:
                    return True
                if value.lower() in ['false', 'no', '0']:
                    return False
                raise Exception('INVALID BOOLEAN VALUE', value)
            if value in [0, 1]:
                return bool(value)
        if type == 'integer':
            if value == '':
                return 0
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.isnumeric():
                return int(value)
        if type == "decimal":
            if isinstance(value, (int, float)):
                return Decimal(str(round(value, 2)))
            if isinstance(value, str):
                try:
                    return round(Decimal(value), 2)
                except (ValueError, TypeError, DecimalException):
                    pass
        if type == 'string':
            if isinstance(value, str):
                return value
        if type == 'json':
            if isinstance(value, (list, dict)):
                return value
            if isinstance(value, str):
                return json.loads(value)
        if type == 'time':
            if isinstance(value, time):
                return value
            try:
                return cls._time_from_isoformat(value)
            except:
                pass
        if type == 'datetime':
            if isinstance(value, datetime):
                return value
            try:
                return cls._datetime_from_isoformat(value)
            except:
                pass
        cls._raise_type_error(type, value)

    @staticmethod
    def _raise_type_error(type, value):
        raise TypeError(f'Imposible to cast "{value}" to "{type}" type')

    @staticmethod
    def _get_DB_compliant(value, type):
        if type in ['boolean', 'integer', 'decimal']:  
            return str(value)
        if type == 'string':
            return value
        if type == 'json':
            return json.dumps(value)
        if type == 'time':
            return value.isoformat()
        if type == 'datetime':
            return value.isoformat() if value else ''
        raise TypeError('INVALID TYPE VALUE')
        
    @classmethod
    def _check_validity(cls, value, type, rules):
        for rule, operand in rules.items():
            if rule == 'max' and value > operand:
                return False
            if rule == 'min' and value < operand:
                return False
            if rule == 'options' and value not in operand:
                return False
            if rule == 'regex' and not re.match(operand, value):
                return False
            if rule == 'JSONschema':
                validate(value, operand)
            if rule == 'function' and not operand(value):
                return False
        return True

    @classmethod
    def _time_from_isoformat(cls, text):
        parsed = re.match('^([0-2]?[0-9]):([0-5]?[0-9])(:([0-5]?[0-9]))?(.([0-9]*))?$', text)
        if parsed:
            hh = int(parsed[1])
            mm = int(parsed[2])
            ss = int(parsed[4]) if parsed[4] else 0
            ms = int(parsed[6]) if parsed[6] else 0
            return time(hh, mm, ss, ms)
        raise Exception('Invalid time format')
    
    @classmethod
    def _datetime_from_isoformat(cls, text):
        if not text:
            return None
        try:
            return datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            raise Exception('Invalid datetime format')

    @classmethod
    def get_list(cls, current_user=None, output='objects', page=None, page_size=1000, model=None, ordered=False, **kwargs):
        return SettingList(Settings.select()).setting_list

    @classmethod
    def _add_from_data_and_user(cls, data, user):
        keys = []
        for key, value in data.items():
            keys.append(key)
            cls.set_setting(key, value, user=user)
        settings = Settings.select().filter(lambda s: s.key in keys)
        return SettingList(settings)

    @classmethod
    def _edit_from_data_and_user(cls, setting, data, user):
        return cls.set_setting(setting.key, data.get('value'), user=user)

    @classmethod
    def get_from_user_and_properties(cls, current_user, name=None, **kwargs):
        obj = Settings.get(key=name)
        if not obj:
            raise NotFound('Setting not found')
        return obj

    @classmethod
    def get_from_user_and_id(cls, current_user, name=None, **kwargs):
        return Settings.get(key=name)
