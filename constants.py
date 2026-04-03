import inspect
import os
import sys
import tempfile
from datetime import date, datetime, timedelta
from typing import Callable, List, NamedTuple
from shared.helpers.new_material_icons import new_icons

import pytz


CLIENT_ABSENT_TOPIC_ID = 1

THIS_YEAR = datetime.now().year
DEFAULT_ACCOUNT_EXPORT_DATE = date(THIS_YEAR, 1, 15)

MAX_INSTALLMENTS_PLANNING = 365*4

PAGELOAD_WARNING_THRESHOLD = 30
PAGELOAD_WARNING_THRESHOLD_API = 60

OLD_REGISTER_NAME = 'OLDREGISTER'
NEW_REGISTER_NAME = 'REGISTER'

MONEY_AMOUNT_PATTERN = r"^[-+]?[0-9]+\.?[0-9]{0,2}0*$"
OPTIONAL_MONEY_AMOUNT_PATTERN = r"^$|^[-+]?[0-9]+(\.[0-9]{0,2})?$"
FLOAT_PATTERN = r"^[-+]?[0-9]+\.?[0-9]*$"
DELAY_DAYS_AMOUNT_PATTERN = r"^$|^[-+]?[0-9]+\.?[0-9]{0,4}0*$"
INTEGER_PATTERN = r"^[-+]?[0-9]+$"
BOOLEAN_PATTERN = r"(?i)^(true|false|1|0)$"
REQUIRED_STRING_PATTERN = r"[^\s]+"
PHONE_PATTERN = "^(\+|00)\d+$"
YEAR_MONTH_PATTERN = r"^(?!0000)\d{4}-(?:0[1-9]|1[0-2])$"
LATITUDE_PATTERN = r"^[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?)$"
LONGITUDE_PATTERN = r"^([-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)|((([1-2]\d{2})|3[0-5][0-9]|360)(\.\d+)?))$"
NAMED_PATTERNS = {
    MONEY_AMOUNT_PATTERN: 'money amount',
    FLOAT_PATTERN: 'float',
    DELAY_DAYS_AMOUNT_PATTERN: 'amount of delayed days',
    INTEGER_PATTERN: 'integer',
    BOOLEAN_PATTERN: 'boolean',
    REQUIRED_STRING_PATTERN: 'not empty string',
    PHONE_PATTERN: 'phone',
    LATITUDE_PATTERN: 'latitude',
    LONGITUDE_PATTERN: 'longitude'
}

NULL_OPTION = [{"type": "null"}]
EMPTY_STRING_OPTION = [{ "type": "string", "maxLength": 0}]
EMPTY_STRING_OPTION_2 = [{ "enum": [ "" ] }]

MONEY_REQUIRED_OPTIONS = [
    {
        "type": "string",
        "pattern": MONEY_AMOUNT_PATTERN
    }, {
        "type": "number",
        "format": "float"
    }
]

OPTIONAL_STRING_OPTIONS = [
    {
        "type": "string",
    }
] + NULL_OPTION

OPTIONAL_DATETIME_OPTIONS = [
    {
        "type": "string",
        "format": "date-time",
    }
] + NULL_OPTION

OPTIONAL_MONEY_OPTIONS = [
    {
        "type": "string",
        "pattern": OPTIONAL_MONEY_AMOUNT_PATTERN
    }, {
        "type": "number",
        "format": "float"
    }
] + NULL_OPTION

OPTIONAL_EMAIL_OPTIONS =  [
    {
        "pattern": "(^$|^([\w\.\-']+)@([\w\-.]+)((\.(\w){2,6})+)$)",
    }
] + NULL_OPTION

BOOLEAN_OPTIONAL_OPTIONS_STRING = [
    {
        "type": "string",
        "pattern": BOOLEAN_PATTERN
    }
] + EMPTY_STRING_OPTION

BOOLEAN_OPTIONAL_OPTIONS = [
    {
        "type": "boolean"
    }
] + NULL_OPTION + BOOLEAN_OPTIONAL_OPTIONS_STRING

INTEGER_REQUIRED_OPTIONS = [
    {
        "type": "string",
        "pattern": INTEGER_PATTERN
    }, {
        "type": "integer"
    }
]

INTEGER_OPTIONAL_OPTIONS_STRING = [
    {
        "type": "string",
        "pattern": INTEGER_PATTERN
    }
] + EMPTY_STRING_OPTION

INTEGER_OPTIONAL_OPTIONS = [
    {
        "type": "integer"
    }
] + INTEGER_OPTIONAL_OPTIONS_STRING + NULL_OPTION

REQUIRED_FLOAT_OPTIONS = [
    {
        "type": "string",
        "pattern": FLOAT_PATTERN
    }, {
        "type": "number",
        "format": "float"
    }
]

FLOAT_OPTIONAL_OPTIONS = REQUIRED_FLOAT_OPTIONS + EMPTY_STRING_OPTION + NULL_OPTION

ENTITIES_OLD_ID_OFFSET = 10000

PICTURE_OPTIONS = [
    {
        "type": "string",
        "minLength": 1,
    }, {
        "type": "integer"
    }, {
        "type": "null"
    }, {
        "type": "string",
        "maxLength": 0
    }
]

MAIN_EXPENSE_CATEGORIES = ['Travel Expense', 'Fuel', 'Accommodation',
                           'Meals, Refresh, Entertainment',
                           'Product Supplies (Battery, Panels, etc.)',
                           'General Supplies (Nails, etc.)', 'Office equipment and furnitures',
                           'Vehicle repairs, maintenance and spares',
                           'Mobile Phone (incl. Airtime)',
                           'Stationary, postage, printing',
                           'Other small items (Sundries)']

ADDITIONAL_EXPENSE_CATEGORIES = ['Research & Development', 'Marketing', 'Cleaning', 'Carriage',
                                 'Bank Charges', 'Internet Expense', 'IT Hardware own use',
                                 'IT Software own use', 'Mobile money fees', 'Salary, NI, Health',
                                 'Biz Rates and Fees', 'Insurance', 'Refund for Client',
                                 'Corp Tax, PAYE Tax, Import Tax, Duty',
                                 'Legal accounting (Audit, layer)', 'Dividends',
                                 'Training, Books, Subs.', 'Charity Donation', 'Employee Commission',
                                 'External Commission', 'Office or shop rent', 'Vehicle Purchase',
                                 'Hardware tools (e.g. hammer)', 'Uncategorized']

OLD_EXPENSE_CATEGORIES = ['Other', 'Mobile Phone', 'Office Equip, Stationary, Postage']

ALL_EXPENSE_CATEGORIES = MAIN_EXPENSE_CATEGORIES+ADDITIONAL_EXPENSE_CATEGORIES

COMPANY_ACCOUNTS = ['Creditors', 'Bank Account', 'Cash Box', 'Mobile Money']

DEFAULT_PAYMENT_RECEPTION_ACCOUNT = 'Mobile Money'

DEPARTMENT_LIST = ['Sales&Marketing', 'Customer Service', 'Tech&Sourcing', 'RH&Admin']

STEP_TYPES = {
    'form': 'Form',
    'workflow': 'Automation',
    'message': 'Message',
    'rich_message': 'Rich Message',
    'create_lead': 'Add/Edit Lead',
    'offer_picker': 'Offer Picker',
    'redirect': 'Redirect',
    'find_lead_or_client': 'Find Lead or Client'
}
CONTRACT_DEVICE_RESTRICTIONS = {
    'require_device': 'All contracts have a stock item',
    'no_device': 'No contracts have a stock item',
    'both': 'Accept both(choose when creating offer)'
}
EDIT_LEAD_OPTIONS = {
    'create_new_lead': 'Create New Lead',
    'edit_lead': 'Edit Lead',
    'create_or_edit_lead': 'Create or Edit Lead'
}

MESSAGE_TYPES = {
    'success': 'Success',
    'warning': 'Warning',
    'info': 'Info',
    'error': 'Error'
}
LEAD_GENERATOR_OPTIONS = {
    'pick': 'The user choses the Lead Generator',
    'user_lg': 'The lead generator of the user is used and the field hidden',
}

OFFERS_HUMAN_READABLE_TYPES = {
    'Loan': 'Paid over time (Loan)',
    'Time Based': 'Subscription (Time-based Service)',
    'Usage Based': 'Pay per use (Usage-based Service)',
    'Lump Sum': 'Paid at once (Lump Sum)',
    None: 'Unknown type'
}

OFFERS_HUMAN_READABLE_TYPES_NEW_SHORT = {
    'Loan': 'Loan',
    'Time Based': 'Time Based Subscription',
    'Usage Based': 'Usage Based Subscription',
    'Lump Sum': 'Paid Upfront',
    None: 'Unknown type'
}

OFFERS_HUMAN_READABLE_TYPES_SHORT = {
    'Loan': 'Loan',
    'Time Based': 'Time Based',
    'Usage Based': 'Usage Based',
    'Lump Sum': 'Lump Sum',
    None: 'Unknown type'
}

WALLET_HUMAN_READABLE_TYPES = {
    'MPESA': 'Mobile Money',
    'Cash': 'Cash',
    'MentorCash': 'Mentor Cash',
    None: 'Unknown type'
}

TIME_BASED_UNITS = ['ABSOLUTE_TIME', 'DAYS']
DEFAULT_UNIT = "DAYS"
OFFLINE_TOKEN_DEFAULT_AMOUNT = 14

DEVICE_MODE_NAMES = {
    1: 'Time',
    2: 'Usage Credit',
    3: 'PAYG Disabled'
}

DEFAULT_GRAPH_BEGIN_DATE = datetime.today()-timedelta(days=365)

# ----- Auth config -----
PIN_LENGTH = 4

ORGANIZATION_LIST = ['Internal', 'External', 'Solaris Offgrid']  # Organization Name

AVAILABLE_ROUTING_ATTRIBUTES = {
    'wallet_name': "Wallet Name",
    'wallet_linked_client': "Wallet Client/Lead (if already linked)",
    'wallet_linked_user': "Wallet User (if already linked)",
    'wallet_phone_number': "Wallet Phone Number",
    'memo': "Payment Memo"
}
AVAILABLE_MATCHING_PARAMETERS = {
    'contract_reference': "Contract Reference",
    'contract_client': "Client/Lead",
    'contract_owner_phone_number': "Client/Lead's Phone Number",
    'user_phone_number': "User's Phone Number",
    'contract_device_serial_number': "Contract/Lead Device Serial Number",
    'addon_reference': "Add-on Reference",
    'custom_id': "{custom_id_name}",
    'pre_registered_device_sn': "Contract/Lead Device Serial Number (Legacy)"
}
AVAILABLE_VALIDITY_CHECK_MODE = {
    'FIND_MATCH': "Find Match",
    'EXTRACT_MATCH': "Extract Match (1st Group)"
}

DAYS_OF_WEEK = {
    0: 'Monday',
    1: 'Tuesday',
    2: 'Wednesday',
    3: 'Thursday',
    4: 'Friday',
    5: 'Saturday',
    6: 'Sunday',
}

MESSAGE_RECIPIENT_OPTIONS = {
    'PAYMENT_NUMBER': 'Phone number of the Payment',
    'PERSON_NUMBER': 'Phone number of the Client/Lead',
    'BOTH': 'Both if they are different'
}

LANGUAGES_NAMES = {
    'EN': 'English',
    'FR': 'French',
    'SW': 'Swahili',
    'PT': 'Portuguese',
    'ES': 'Spanish',
    'AM': 'Amharic',
    'ZH': 'Chinese',
    'BE': 'Bearnais'
}

AVAILABLE_WEB_LANGUAGES = {
    'EN': 'English',
    'FR': "French",
    'SW': 'Swahili (BETA)',
    'PT': 'Portuguese',
    'ES': 'Spanish (BETA)',
    'AM': 'Amharic (BETA)',
    'ZH': 'Chinese (BETA)',
    'BE': 'Bearnais (BETA)'
}

AVAILABLE_USERS_LANGUAGES = AVAILABLE_WEB_LANGUAGES # Currently true but doesnt have to be

AVAILABLE_USERS_SMS_LANGUAGES = ['EN', 'FR', 'SW', 'PT', 'ES', 'AM', 'ZH', 'BE']

AVAILABLE_CLIENTS_SMS_LANGUAGES = ['EN', 'FR', 'SW', 'PT', 'ES', 'AM', 'ZH', 'BE', 'CU']

AVAILABLE_DEVICE_API_TYPES = {
    "ONE_WAY_CODE": 'One Way Code Device',
    "TWO_WAY_CODE": 'Two Way Code Device',
    "GSM": 'Radio Device'
}

AVAILABLE_DEVICE_API_OFFLINE_SUPPORT = {
    'ENABLED': 'Enabled',
    'DISABLED': 'Disabled'
}

AVAILABLE_SUPPORTED_OFFER_TYPES = {
    'TIME_BASED': 'Time Based',
    'USAGE_BASED': 'Usage Based',
    'BOTH': 'Both'
}

GPS_SURFACE_MEASUREMENT_UNITS = {
    'm2': 'Square Meters (m2)',
    'ha': 'Hectares (ha)',
    'acre': 'Acres'
}

MONTHLY_PAYMENT_FREQUENCY = 'MONTHLY'
DAILY_PAYMENT_FREQUENCY = 'DAILY'

AVAILABLE_OFFER_PAYMENT_FREQUENCIES = {
    DAILY_PAYMENT_FREQUENCY: 'Daily',
    MONTHLY_PAYMENT_FREQUENCY: 'Monthly'
}

AVAILABLE_DEVICE_API_VERIONS = ["v1", "v2"]

SYNC_METHOD_CODES = {
    "ONE_WAY_CODE": 1,
    "TWO_WAY_CODE": 2,
    "GSM": 3,
    'LORA': 4,
    'MOBILE': 5
}

AVAILABLE_TIMEZONES = pytz.all_timezones
AVAILABLE_TIMEZONES_LIST = {tz: tz for tz in AVAILABLE_TIMEZONES if 'GMT' not in tz}

def router_rule(attr, param, strict=True, validity_check='', validity_check_mode='', prepend=''):
    return {
        'routing_attribute': attr,
        'matching_parameter': param,
        'strict': strict,
        'validity_check': validity_check,
        'validity_check_mode': validity_check_mode,
        'append': '',
        'prepend': prepend,
        'ignore_prefix': False
    }

ROUTING_CONFIG = {
    '1': router_rule('wallet_name', 'contract_reference'),
    '2': router_rule('memo', 'contract_reference', True, "(?i)c([0-9]{4,})", "EXTRACT_MATCH", 'C'),
    '3': router_rule('memo', 'contract_device_serial_number', False, '[/a-zA-Z0-9-]{4,20}'),
    '4': router_rule('memo', 'contract_owner_phone_number'),
    '5': router_rule('wallet_linked_client', 'contract_client'),
    '6': router_rule('wallet_phone_number', 'contract_owner_phone_number'),
}

HIDE_PREFIX_FALLBACK_DEVICE_TYPE_OPTIONS = {
    True: 'Yes',
    False: 'No'
}

NPG_DEVICE_ENABLED_OPTIONS = {
    True: 'Yes',
    False: 'No'
}

LEAD_INFO_BOOLEAN_OPTIONS = {
    'true': 'Yes',
    'false': 'No'
}

CONFLICT_RESOLUTION_OPTIONS = {
    'ASK': 'Ask (or force mobile if global sync)', 
    'FORCE_MOST_RECENT': 'Force Most Recent',
    'FORCE_WEB': 'Force Web',
    'FORCE_MOBILE': 'Force Mobile'
}

CURRENT_DIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, PARENT_DIR)
# Path to the JSON translation files (client_msg, msg, js_msg, etc.)
# We explicitly include the `oss/` segment to match the actual location of:
#   `oss/shared/services/translations/<LANG>/<LANG>_client_msg.json`
TRANSLATION_FOLDER = os.path.join(CURRENT_DIR, 'shared/services/translations/')

WEB_STATIC_PATH = os.path.join(CURRENT_DIR, 'web_app/static/')
IMG_STATIC_PATH = os.path.join(CURRENT_DIR, 'web_app/static/img/')
DATA_PATH = os.path.join(PARENT_DIR, 'data/')
TEMP_PATH = os.path.join(PARENT_DIR, 'temp/')
BACKUP_PATH = os.path.join(PARENT_DIR, 'backup/')
ANALYTICAL_DB_BACKUP_PATH = os.path.join(BACKUP_PATH, 'analytical_db/')
MOBILE_UPDATES_PATH = os.path.join(PARENT_DIR, 'mobile_updates/')
CONTENT_PATH = os.path.join(DATA_PATH, 'content/')
PICTURE_PATH = os.path.join(CONTENT_PATH, '')
ACTIVITY_LOG_PATH = os.path.join(CONTENT_PATH, 'activity_log/')
LOGO_FILE_NAME = 'custom_logo.jpg'
LOGO_PATH = CONTENT_PATH+LOGO_FILE_NAME
LOGO_FILE_NAME_INVERTED = 'custom_logo_inverted.jpg'
LOGO_INVERTED_PATH = CONTENT_PATH+LOGO_FILE_NAME_INVERTED
sys.path.insert(0, DATA_PATH)
ANALYTICAL_DB_POSTGRES_FILENAME = 'analytical_db_latest.sql'
ANALYTICAL_DB_SSL_CERT = '/setup_data/server.crt'
ANALYTICAL_DB_ROOT_SSL_CERT = '/setup_data/root_ca.crt'

RECEIPT_PICTURES_PATH = os.path.join(CONTENT_PATH, 'receipt_scans/')


# ------ Logs settings ------
if os.getenv('ENV_VAR') in ['TEST']:
    LOGS_DIR = tempfile.mkdtemp()
else:
    LOGS_DIR = '{}logs'.format(DATA_PATH)

WEBSERVER_LOG_PATH = os.path.join(LOGS_DIR, 'WebAppErrorJSON.log')
MOBILE_API_LOG_PATH = os.path.join(LOGS_DIR, 'MobileAPIErrorJSON.log')
ACCESS_LOG_PATH = os.path.join(LOGS_DIR, 'access.log')
WEBHOOK_LOG_PATH = os.path.join(LOGS_DIR, 'webhook.log')

# Specific action logs
LOGIN_LOG_PATH = os.path.join(LOGS_DIR, 'LoginJSON.log')
MANUAL_PAYMENT_LOG_PATH = os.path.join(LOGS_DIR, 'ManualPaymentJSON.log')
MANUAL_MESSAGE_LOG_PATH = os.path.join(LOGS_DIR, 'ManualMessageJSON.log')


# -------Mobile API Settings -----
MOBILE_HELP_FILES_PATH = MOBILE_UPDATES_PATH + 'help'

# Overall API config
API_PORT = 6789
API_ROUTE = 'payg_api'
API_PREFIX = '/api/v1'
BASE_PLATFORM_NAME = 'PaygOps'

# Hooks config
HOOK_CONFIGURATION_FILE = os.path.join(DATA_PATH, 'hooks_subscriptions.json')
ALLOWED_HOOKS = [
    'client_registered', 'client_deregistered', 'contract_cancelled', 'client_edited', 'new_issue',
    'issue_closed', 'outgoing_message', 'lead_added', 'lead_edited', 'custom_form_answered',
    'new_interaction', 'device_swapped', 'unknown_user_sms_command',
    'unknown_client_sms_command', 'undo_contract_default',
    'new_payment', 'new_orphaned_payment', 'new_contract_payment', 'new_lead_payment',
    'new_addon_payment', 'new_user_payment', 'user_created', 'user_edited', 
    'contract_defaulted', 'new_addon_offer', 'new_addon_offer_version', 'new_stock_movement',
    'new_addon', 'discount_given', 'delay_given', 'offer_changed', 'contract_payment',
    'token_generated','new_reconciliation', 'addon_approved', 'contract_paused',
    'contract_resumed','addon_cancelled', 'addon_delivered', 'addon_undelivered',
    'addon_planned_delivery_date_change', 'contract_overpaid', 'custom_form_answered_uploaded', 
    'task_created', 'task_edited', 'contract_completed'
]


DATA_EXPORTS_CONFIG = {
    'client_data': {
        "name": "Clients Data",
        "model": "Clients"
    },
    'user_data': {
        "name": "Users Data",
        "model": "Users"
    },
    'lead_data': {
        "name": "Leads Data",
        "model": "Leads"
    },
    'lead_generator_data': {
        "name": "Lead Generators Data",
        "model": "Lead_Generators"
    },
    'contract_data': {
        "name": "Contracts Data",
        "model": "Contracts"
    },
    'repayment_data': {
        "name": "Contract Payments Data",
        "model": "Contract_Payments"
    },
    'contract_event_data': {
        "name": "Contract Events Data",
        "model": "Contract_Events"
    },
    'offers_data': {
        "name": "Contract Offers Data",
        "model": "Contract_Offers"
    },
    'reconciled_payment_data': {
        "name": "Reconciled Payments Data",
        "model": "Reconciled_Payments"
    },
    'payments_data': {
        "name": "Payments Data",
        "model": "Payments"
    },
    'village_data': {
        "name": "Operational Entities Data",
        "model": "Operational_Entities"
    },
    'interaction_data': {
        "name": "Interactions Data",
        "model": "Interactions"
    },
    'issue_data': {
        "name": "Issues Data",
        "model": "Issues"
    },
    'stock_data': {
        "name": "Stock Data",
        "model": "Stock_Items"
    },
    'stock_movements_data': {
        "name": "Stock Movements Data",
        "model": "Stock_Movements"
    },
    'addons_data': {
        "name": "Add-ons Data",
        "model": "AddOns"
    },
    'product_subtypes_data': {
        "name": "Product Sub-types",
        "model": "Product_SubTypes"
    },
    'custom_forms_data': {
        "name": "Custom Forms Data",
        "model": "Question_Answers"
    },
    'payment_wallets_data':{
        "name": "Payment Wallets Data",
        "model": "Payment_Wallets"
    },
    'reversed_payments_data':{
        "name": "Reversed Payments Data",
        "model": "Reversed_Payments"
    },
    'add_on_offer_data':{
        "name":"Add On Offers Data",
        "model":"AddOn_Offers"
    },
    'task_data':{
        "name":"Task Data",
        "model":"Tasks",
        "tag":"beta"
    },
    'task_type_data': {
        "name":"Task Type Data",
        "model":"Task_Types",
        "tag":"beta"
    },
    'quantity_stock_items': {
        "name":"Quantity Stock Items",
        "model":"Quantity_Stock_Items"
    },
    'quantity_stock_movements': {
        "name":"Quantity Stock Movements",
        "model":"Quantity_Stock_Movements"
    }
}

DATA_EXPORT_LIMIT = 1000000

PERSONAL_INFO_FIELDS_WITH_DEFAULT = ['verbal_language', 'home_use', 'business_use', 'preferred_sms_language', 'status', 'reasons_for_not_buying', 'birthdate']


def entity_config(name, names, enabled):
    return {
        "name": name,
        "names": names,
        "enabled": enabled
    }

OPERATIONAL_ENTITIES_CONFIG = [
    {"name": "Village", "names": "Villages"},
    entity_config("Cluster", "Clusters", True),
    entity_config("Hub", "Hubs", True),
    entity_config("Zone", "Zones", False if os.getenv('ENV_VAR') in ['TEST'] else True),
    entity_config("Region", "Regions", False if os.getenv('ENV_VAR') in ['TEST'] else True) 
]

MAX_ENTITY_LEVEL = len(OPERATIONAL_ENTITIES_CONFIG)-1

ENTITIY_LEVEL_SELECT = {}

# Add levels dynamically based on MAX_ENTITY_LEVEL
for i in range(MAX_ENTITY_LEVEL + 1):
    ENTITIY_LEVEL_SELECT[str(i)] = f"Level {i}"

ALLOWED_EXTENSIONS = set(['jpg', 'jpeg', 'JPG', 'JPEG'])

AJAX_SELECT_THRESHOLD = 250
AJAX_SELECT_CLASS = 'ajax'

COMPUTED_SORTING_THRESHOLD = 1000

SMS_EDITOR_CATEGORY_COMMON = 'common'
SMS_EDITOR_CATEGORY_LOAN = 'loan'
SMS_EDITOR_CATEGORY_LUMP_SUM = 'lump_sum'
SMS_EDITOR_CATEGORY_TIME_BASED = 'time_based'
SMS_EDITOR_CATEGORY_USAGE_BASED = 'usage_based'

SMS_EDITOR_CATEGORY_NAMES = {
    SMS_EDITOR_CATEGORY_COMMON: 'Common',
    SMS_EDITOR_CATEGORY_LOAN: 'Loan',
    SMS_EDITOR_CATEGORY_LUMP_SUM: 'Lump Sum',
    SMS_EDITOR_CATEGORY_TIME_BASED: 'Time Based',
    SMS_EDITOR_CATEGORY_USAGE_BASED: 'Usage Based'
}

GENDER_NAMES = {
    1: 'Male',
    2: 'Female'
}

GENDER_IDS = {
    'male': 1,
    'female': 2,
    'Unknown': 3
}

PLATFORM_TYPES = {
    'premium': 'Premium',
    'new-premium': 'New Premium',
    'freemium-demo': 'Demo',
    'features-package':"Features Package"
}

NON_SERIALIZED_ITEMS_ORIGIN = {
    'user': 'User',
    'orphaned': 'Orphaned',
    'operational-entities': 'Operational Entities'
}

CUSTOMISABLE_MSGS_SECTIONS = {
    SMS_EDITOR_CATEGORY_COMMON: {
        'Sales Proccess': [
            'LEAD_NOT_AWAITING_PAYMENT',
            'LEAD_APPROVED_AND_AWAITING_PAYMENT',
            'LEAD_INSUFFICIENT_BALANCE',
            'LEAD_PAY_DEPOSIT_SUCCESS',
            'ADDON_PAYMENT_INSUFFICIENT_BALANCE',
            'ADDON_PAYMENT_SUCCESS',
            'ADDITIONAL_DOWN_PAYMENT_REQUIRED',
            'CONTRACT_CANCELLED',
        ],
        'Payments': [
            'PAYMENT_RECEIVED',
            'PAYMENT_RECEIVED_UNKNOWN',
            'ACTIVATION_REQUEST_SUCCESS',
            'ACTIVATION_REQUEST_SUCCESS_NO_CODE',
            'NO_ACTIVATION_TIME_ON_DEVICE',
            'CASH_PAYMENT_SUCCESS_CLIENT',
            'CASH_PAYMENT_SUCCESS_LEAD',
            'PAYMENT_REVERSED_SETTING_ENABLED',
            'PAYMENT_REVERSED_SETTING_DISABLED',
            'PAYMENT_FOR_PAUSED_CONTRACT_SETTING_ENABLED',
            'PAY_CLIENT_SUCCESS_MOBILE_MONEY'
        ],
        'Payments Reminders': [
            'PAYMENT_REMINDER_SMS_SOON',
            'PAYMENT_REMINDER_SMS_TODAY',
            'PAYMENT_REMINDER_SMS_TOMORROW',
            'PAYMENT_REMINDER_SMS_PAST'
        ],
        'Contract Status Changes': [
            'CONTRACT_PAUSE_SUCCESS_SMS',
            'CONTRACT_RESUME_SUCCESS_SMS',
        ],
        'Others': [
            'UNKNOWN_REQUEST',
            'UNKNOWN_SENDER',
            'DEVICE_TYPE_NOT_SPECIFIED',
            'DEVICE_PAIRING_SUCCESS',
            'DEVICE_PAIRING_SUCCESS_NO_CODE'
        ]
    },
    SMS_EDITOR_CATEGORY_LOAN: {
        'Loan Offers - Paid over time': [
            'WELCOME_MESSAGE',
            'WELCOME_MESSAGE_NO_CODE'
        ],
        'Payments': [
            'ACTIVATION_TIME_BOUGHT',
            'ACTIVATION_TIME_BOUGHT_NO_TOKEN',
            'BALANCE_INSUFFICIENT_LOAN',
        ],
        'Loan Completed': [
            'LOAN_REPAYMENT_COMPLETED',
            'LOAN_REPAYMENT_COMPLETED_NO_TOKEN',
            'LOAN_REPAYMENT_COMPLETED_UNLOCK_DISABLED',
            'AUTO_DISABLE_PAYG_SUCCESS',
            'AUTO_DISABLE_PAYG_SUCCESS_NO_CODE',
            'AUTO_DISABLE_PAYG_DISABLED',
            'LOAN_OVERPAYMENT'
        ],
        'Loan Terms Change': [
            'LOAN_DURATION_CHANGE',
            'LOAN_PRICING_CHANGE',
            'LOAN_DURATION_CHANGE_NO_VALUE'
        ]
    },
    SMS_EDITOR_CATEGORY_LUMP_SUM: {
        'Lump Sum Offers - Paid at once': [
            'WELCOME_MESSAGE_LUMP_SUM',
            'WELCOME_MESSAGE_LUMP_SUM_NO_CODE'
        ]
    },
    SMS_EDITOR_CATEGORY_TIME_BASED: {
        'Time Based Offers - Subscription': [
            'WELCOME_MESSAGE_TIME_BASED',
            'WELCOME_MESSAGE_TIME_BASED_NO_CODE'
        ],
        'Payments': [
            'CONTRACT_PAYMENT_MADE',
            'CONTRACT_PAYMENT_MADE_NO_TOKEN',
            'CONTRACT_PAYMENT_MADE_MONTHLY',
            'CONTRACT_PAYMENT_MADE_MONTHLY_NO_TOKEN',
            'BALANCE_INSUFFICIENT',
        ],
    },
    SMS_EDITOR_CATEGORY_USAGE_BASED: {
        'Usage Based Offer - Pay per Use': [
            'WELCOME_MESSAGE_USAGE_BASED',
            'WELCOME_MESSAGE_USAGE_BASED_NO_CODE'
        ],
        'Payments': [
            'CONTRACT_PAYMENT_MADE_USAGE_BASED',
            'CONTRACT_PAYMENT_MADE_USAGE_BASED_NO_TOKEN',
            'CREDIT_ACTIVATION_REQUEST_SUCCESS',
            'CREDIT_ACTIVATION_REQUEST_SUCCESS_NO_CODE',
            'BALANCE_INSUFFICIENT',
        ],
    }
}

LOAN_STATUS_VARIABLE_SHORT = [
    'expiration_time_day', 'expiration_time_month',
    'expiration_time_year', 'total_to_pay', 'total_to_pay_with_addons',
    'remaining_due', 'remaining_due_with_addons', 'remaining_due-pending_amount',
    'remaining_due_with_addons-pending_amount', 'paid_so_far', 'paid_so_far+pending_amount', 'paid_so_far_with_addons',
    'paid_so_far_with_addons+pending_amount', 'reference_payment', 'minimum_payment', 'next_payment_price', 'minimum_payment-pending_amount', 'pending_amount',
    'currency_sym', 'expected_paid', 'amount_in_arrears', 'contract_reference', 'client_phone_number', 'device_serial',
    'expected_maturity_day', 'expected_maturity_month', 'expected_maturity_year']

LOAN_STATUS_VARIABLES = ['offer_name', 'weeks_paid', 'days_paid', 'weeks_to_pay',
                         'days_to_pay', 'remaining_weeks_to_pay', 'remaining_days_to_pay'] + LOAN_STATUS_VARIABLE_SHORT

PAYMENT_REMINDER_VARIABLES = ['reference_payment', 'days_before_expiry', 'name', 'surname', 'offer_name',
                              'minimum_payment', 'minimum_payment-pending_amount', 'next_payment_price', 'currency_sym', 'pending_amount', 'amount_in_arrears',
                              'contract_reference', 'client_phone_number', 'device_serial',
                              'expected_maturity_day', 'expected_maturity_month', 'expected_maturity_year']

CUSTOMISABLE_MSGS_INFO = {
    'LEAD_NOT_AWAITING_PAYMENT': {
        'name': 'Lead not yet approved',
        'description': 'When a lead that is not yet approved tries to pay the downpayment',
        'variables': []
    },
    
    'LEAD_APPROVED_AND_AWAITING_PAYMENT': {
        'name': 'Lead approved',
        'description': 'When a lead is approved and their offer requires a downpayment to be made',
        'variables': ['deposit_value', 'still_to_pay', 'name', 'surname', 'offer_name', 'free_time', 'currency_sym', 'contract_reference']
    },
    'LEAD_INSUFFICIENT_BALANCE': {
        'name': 'Lead insufficient balance',
        'description': 'When a lead\'s downpayment is insufficient',
        'variables': ['already_paid', 'still_to_pay', 'deposit_value', 'currency_sym', 'contract_reference','transaction_id']
    },
    'LEAD_PAY_DEPOSIT_SUCCESS': {
        'name': 'Lead pay deposit success',
        'description': 'When a lead has successfully paid the downpayment',
        'variables': ['deposit_value', 'currency_sym', 'balance','transaction_id']
    },
    'PAY_CLIENT_SUCCESS_MOBILE_MONEY': {
        'name': 'Mobile Money Payment',
        'description': 'When a client makes a payment using mobile money',
        'variables': ['amount', 'currency_sym', 'transaction_id', 'balance', 'name', 'surname', 'contract_reference', 'client_phone_number']
    },
    'WELCOME_MESSAGE_LUMP_SUM': {
        'name': 'Welcome message (Lump sum)',
        'description': 'When a new client is registered on a Lump Sum (Paid at once) offer ',
        'variables': ['registration_answer_code', 'name', 'surname', 'device_serial', 'offer_name', 'contract_reference']
    },
    'WELCOME_MESSAGE_LUMP_SUM_NO_CODE': {
        'name': 'Welcome message (Lump sum - No token)',
        'description': 'When a new client is registered on a Lump Sum (Paid at once) offer for a device that has no tokens (e.g. cookstove or GSM device)',
        'variables': ['name', 'surname', 'device_serial', 'offer_name', 'contract_reference']
    },
    'WELCOME_MESSAGE': {
        'name': 'Welcome message (Loan)',
        'description': 'When a new client is registered and a token has been generated (sent to the client)',
        'variables': ['name', 'surname', 'registration_answer_code', 'activation_answer_code',
                      'device_serial', 'free_time', 'offer_name'] + LOAN_STATUS_VARIABLE_SHORT
    },
    'WELCOME_MESSAGE_NO_CODE': {
        'name': 'Welcome message (Loan - No token)',
        'description': 'When a new client is registered with a device that has no tokens (e.g. cookstove or GSM device)',
        'variables': ['name', 'surname', 'device_serial', 'free_time', 'offer_name'] + LOAN_STATUS_VARIABLE_SHORT
    },
    'WELCOME_MESSAGE_TIME_BASED': {
        'name': 'Welcome message (Time based)',
        'description': 'When a new client is registered and a token has been generated (sent to the client)',
        'variables': ['expiration_time_day', 'expiration_time_month', 'expiration_time_year', 'registration_answer_code', 'activation_answer_code',
                        'name', 'surname', 'device_serial', 'free_time', 'offer_name', 'contract_reference']
    },
    'WELCOME_MESSAGE_TIME_BASED_NO_CODE': {
        'name': 'Welcome message (Time based - No token)',
        'description': 'When a new client is registered with a device that has no tokens (e.g. cookstove or GSM device)',
        'variables': ['expiration_time_day', 'expiration_time_month', 'expiration_time_year',
                      'name', 'surname', 'device_serial', 'free_time', 'offer_name', 'contract_reference']
    },
    'WELCOME_MESSAGE_USAGE_BASED': {
        'name': 'Welcome message (Usage based)',
        'description': 'When a new client is registered and a token has been generated (sent to the client)',
        'variables': ['registration_answer_code', 'activation_answer_code',
                        'name', 'surname', 'device_serial', 'free_credit', 'credit_unit', 'offer_name', 'contract_reference']
    },
    'WELCOME_MESSAGE_USAGE_BASED_NO_CODE': {
        'name': 'Welcome message (Usage based - No token)',
        'description': 'When a new client is registered with a device that has no tokens (e.g. cookstove or GSM device)',
        'variables': ['name', 'surname', 'device_serial', 'free_credit', 'credit_unit', 'offer_name', 'contract_reference']
    },
    'CONTRACT_PAYMENT_MADE': {
        'name': 'Contract payment made (day-based offer - With Token) (Time based)',
        'description': 'After a payment to a device that activates with tokens, if the amount allows a contract payment. Usually sent together with Payment Received',
        'variables': ['amount_paid', 'currency_sym', 'device_serial', 'offer_name', 'expiration_time_day', 'expiration_time_month',
                      'expiration_time_year', 'days_bought', 'days_bought_rounded', 'hours_bought', 'name', 'surname',
                      'expected_paid', 'paid_so_far', 'amount_in_arrears', 'minimum_payment', 'reference_payment', 'contract_reference','transaction_ids', 'activation_answer_code']
    },
    'CONTRACT_PAYMENT_MADE_NO_TOKEN': {
        'name': 'Contract payment made (day-based offer - No Token) (Time based)',
        'description': 'After a payment to a device that does not activate with tokens, if the amount allows a contract payment. Usually sent together with Payment Received',
        'variables': ['amount_paid', 'currency_sym', 'device_serial', 'offer_name', 'expiration_time_day', 'expiration_time_month',
                      'expiration_time_year', 'days_bought', 'days_bought_rounded', 'hours_bought', 'name', 'surname',
                      'expected_paid', 'paid_so_far', 'amount_in_arrears', 'minimum_payment', 'reference_payment', 'contract_reference','transaction_ids']
    },
    'CONTRACT_PAYMENT_MADE_MONTHLY': {
        'name': 'Contract payment made (month-based offer - With Token) (Time based)',
        'description': 'After a payment to a device that activates with tokens, if the amount allows a contract payment. Usually sent together with Payment Received',
        'variables': ['amount_paid', 'currency_sym', 'device_serial', 'offer_name', 'expiration_time_day', 'expiration_time_month',
                      'expiration_time_year', 'days_bought_rounded', 'name', 'surname',
                      'expected_paid', 'paid_so_far', 'amount_in_arrears', 'minimum_payment', 'reference_payment', 'contract_reference','transaction_ids', 'activation_answer_code']
    },
    'CONTRACT_PAYMENT_MADE_MONTHLY_NO_TOKEN': {
        'name': 'Contract payment made (month-based offer - No Token) (Time based)',
        'description': 'After a payment to a device that does not activate with token, if the amount allows a contract payment. Usually sent together with Payment Received',
        'variables': ['amount_paid', 'currency_sym', 'device_serial', 'offer_name', 'expiration_time_day', 'expiration_time_month',
                      'expiration_time_year', 'days_bought_rounded', 'name', 'surname',
                      'expected_paid', 'paid_so_far', 'amount_in_arrears', 'minimum_payment', 'reference_payment', 'contract_reference','transaction_ids']
    },
    'CONTRACT_PAYMENT_MADE_USAGE_BASED': {
        'name': 'Contract payment made (Usage based - With Token)',
        'description': 'After a payment to a device that activates with tokens, if the amount allows a contract payment. Usually sent together with Payment Received',
        'variables': ['amount_paid', 'currency_sym', 'device_serial', 'offer_name', 'name', 'surname',
                      'credit_unit', 'credit_bought', 'minimum_payment', 'reference_payment', 'contract_reference', 'paid_so_far','transaction_ids', 'activation_answer_code']
    },
    'CONTRACT_PAYMENT_MADE_USAGE_BASED_NO_TOKEN': {
        'name': 'Contract payment made (Usage based - No Token)',
        'description': 'After a payment to a device that does not activate with tokens, if the amount allows a contract payment. Usually sent together with Payment Received',
        'variables': ['amount_paid', 'currency_sym', 'device_serial', 'offer_name', 'name', 'surname',
                      'credit_unit', 'credit_bought', 'minimum_payment', 'reference_payment', 'contract_reference', 'paid_so_far','transaction_ids']
    },
    'PAYMENT_RECEIVED': {
        'name': 'Payment received',
        'description': 'After a payment is received from a client (by mobile money)',
        'variables': ['amount', 'currency_sym', 'balance', 'name', 'surname','transaction_id']
    },
    'PAYMENT_REVERSED_SETTING_ENABLED': {
        'name': 'Contract payment reversed (setting enabled)',
        'description': 'After a contract payment is reversed (including downpayments when the setting "Allow contract repayments after downpayment reversal" is enabled)',
        'variables': ['amount', 'currency_sym', 'contract_reference', 'name', 'surname','transaction_id']
    },
    'PAYMENT_REVERSED_SETTING_DISABLED': {
        'name': 'Contract downpayment payment reversed (setting disabled)',
        'description': 'After a downpayment is reversed if the setting "Allow contract repayments after downpayment reversal" is disabled',
        'variables': ['amount', 'currency_sym', 'name', 'surname','transaction_id', 'contract_reference']
    },
    'PAYMENT_FOR_PAUSED_CONTRACT_SETTING_ENABLED': {
        'name': 'Contract payment made for paused contract (setting enabled)',
        'description': 'After a payment is made for a paused contract if the allow contract payments for paused contracts setting is enabled',
        'variables': ['amount', 'name', 'surname', 'contract_reference', 'device_serial', 'offer_name', 'weeks_to_pay', 'days_to_pay', 
                        'remaining_weeks_to_pay', 'remaining_days_to_pay', 'expiration_time_day','total_to_pay', 'pending_amount','remaining_due',
                        'already_paid', 'paid_so_far+pending_amount', 'next_payment_price', 'expected_paid', 'amount_in_arrears', 'remaining_due-pending_amount']
    },
    'CASH_PAYMENT_SUCCESS_CLIENT': {
        'name': 'Payment collected (cash) for client',
        'description': 'After a payment is collected from a client (by a User)',
        'variables': ['amount', 'currency_sym', 'name', 'surname','transaction_id', 'client_id', 'commission']
    },
    'CASH_PAYMENT_SUCCESS_LEAD': {
        'name': 'Payment collected (cash) for lead',
        'description': 'After a payment is collected from a lead (by a User)',
        'variables': ['amount', 'currency_sym', 'name', 'surname','transaction_id', 'lead_id', 'commission']
    },
    'ADDON_PAYMENT_INSUFFICIENT_BALANCE': {
        'name': 'Add-on payment with insufficient balance',
        'description': 'After a payment is reconciled with an add-on but the amount is not enough',
        'variables': ['total_amount', 'reference', 'already_paid', 'remaining_to_pay', 'currency_sym','transaction_id']
    },
    'ADDON_PAYMENT_SUCCESS': {
        'name': 'Add-on payment successful',
        'description': 'After a payment reconciled with an add-on successfully',
        'variables': ['total_amount', 'reference', 'balance', 'currency_sym','transaction_id']
    },
    'ADDITIONAL_DOWN_PAYMENT_REQUIRED': {
        'name': 'Additional down payment required',
        'description': 'When the downpayment is increased and the amount paid by the lead is insufficient', 
        'variables': ['amount', 'already_paid', 'still_to_pay', 'currency_sym']
    },
    'LOAN_DURATION_CHANGE': {
        'name': 'Loan duration change',
        'description': 'After a loan add-on is added to a contract changing the total value and its duration',
        'variables': ['total_to_pay', 'old_total_to_pay', 'duration', 'old_duration', 'minimum_payment', 'reference_payment', 'currency_sym', 'expected_maturity_day','expected_maturity_month', 'expected_maturity_year']
    },
    'LOAN_PRICING_CHANGE': {
        'name': 'Loan pricing change',
        'description': 'After a loan add-on is added to a contract changing the total value and the repayment amount',
        'variables': ['total_to_pay', 'old_total_to_pay', 'minimum_payment', 'reference_payment', 'old_reference_payment', 'reference_credit', 'duration', 'currency_sym', 'expected_maturity_day','expected_maturity_month', 'expected_maturity_year']
    },
    'LOAN_DURATION_CHANGE_NO_VALUE': {
        'name': 'Loan duration and repayment change (no added value)',
        'description': 'After an add-on of type "Contract Duration Change" is added, modifying the duration and the reference pricing of the contract but without adding extra value.',
        'variables': ['total_to_pay', 'minimum_payment', 'reference_payment', 'old_reference_payment', 'reference_credit', 'old_duration', 'duration', 'currency_sym', 'expected_maturity_day','expected_maturity_month', 'expected_maturity_year']
    },
    'PAYMENT_RECEIVED_UNKNOWN': {
        'name': 'Payment received - Unknown',
        'description': 'After a payment is received from an unknown client',
        'variables': ['amount', 'currency_sym', 'balance','transaction_id']
    },
    'ACTIVATION_TIME_BOUGHT': {
        'name': 'Contract payment made (Loan - With Token)',
        'description': 'After a payment to a device that activates with tokens if the amount allows a contract payment. Usually sent together with Payment Received',
        'variables': ['name', 'surname', 'amount_paid', 'device_serial',
                      'days_bought', 'days_bought_rounded', 'hours_bought', 'transaction_ids', 'activation_answer_code'] + LOAN_STATUS_VARIABLES
    },
    'ACTIVATION_TIME_BOUGHT_NO_TOKEN': {
        'name': 'Contract payment made (Loan - No Token)',
        'description': 'After a payment to a device that does not activate with tokens, if the amount allows a contract payment. Usually sent together with Payment Received',
        'variables': ['name', 'surname', 'amount_paid', 'device_serial',
                      'days_bought', 'days_bought_rounded', 'hours_bought', 'transaction_ids'] + LOAN_STATUS_VARIABLES
    },
    'ACTIVATION_REQUEST_SUCCESS': {
        'name': 'Device Activation',
        'description': 'Message sent with the token to activate the device.',
        'variables': ['activation_answer_code', 'expiration_time_day', 'expiration_time_month', 'expiration_time_year', 'contract_reference']
    },
    'ACTIVATION_REQUEST_SUCCESS_NO_CODE': {
        'name': 'Device Activation (No token)',
        'description': 'Message sent for a device that has no tokens (e.g. cookstove or GSM device).',
        'variables': ['expiration_time_day', 'expiration_time_month', 'expiration_time_year', 'contract_reference']
    },
    'CREDIT_ACTIVATION_REQUEST_SUCCESS': {
        'name': 'Usage-based Device Activation',
        'description': 'Message sent with the token to activate the device.',
        'variables': ['activation_answer_code', 'credit_bought', 'credit_unit', 'contract_reference']
    },
    'CREDIT_ACTIVATION_REQUEST_SUCCESS_NO_CODE': {
        'name': 'Usage-based Device Activation (No token)',
        'description': 'Message sent for a device that has no tokens (e.g. cookstove or GSM device).',
        'variables': ['expiration_time_day', 'credit_bought', 'credit_unit', 'contract_reference']
    },
    'NO_ACTIVATION_TIME_ON_DEVICE': {
        'name': 'No Activation Time on Device',
        'description': 'The device cannot be activated because activation time has expired',
        'variables': ['expiration_time_day', 'expiration_time_month', 'expiration_time_year', 'contract_reference']
    },
    'DEVICE_PAIRING_SUCCESS': {
        'name': 'Device Pairing',
        'description': 'Message sent with the pairing code to pair the device.',
        'variables': ['pairing_answer_code', 'contract_reference', 'device_serial']
    },
    'DEVICE_PAIRING_SUCCESS_NO_CODE': {
        'name': 'Device Pairing (No token)',
        'description': 'Message sent for a device that has already been paired.',
        'variables': ['contract_reference', 'device_serial']
    },
    'BALANCE_INSUFFICIENT': {
        'name': 'Insufficient amount to make contract payment',
        'description': 'After a payment, if the amount is below the minimum contract payment amount. Usually sent together with Payment Received',
        'variables': ['name', 'surname', 'currency_sym', 'minimum_payment', 'reference_payment', 'minimum_payment-pending_amount', 'pending_amount','transaction_id']
    },
    'BALANCE_INSUFFICIENT_LOAN': {
        'name': 'Insufficient amount to make contract payment (Loan)',
        'description': 'After a payment, if the amount is below the minimum contract payment amount. Usually sent together with Payment Received',
        'variables': ['name', 'surname', 'currency_sym', 'minimum_payment', 'reference_payment', 'minimum_payment-pending_amount', 'pending_amount','transaction_id'] + LOAN_STATUS_VARIABLES
    },
    'PAYMENT_REMINDER_SMS_SOON': {
        'name': 'Payment reminder - Due in some days',
        'description': 'When a client needs to pay in the next few days (number of days can be customized)',
        'variables': PAYMENT_REMINDER_VARIABLES
    },
    'PAYMENT_REMINDER_SMS_TOMORROW': {
        'name': 'Payment reminder - Due Tomorrow',
        'description': 'When a client needs to pay tomorrow',
        'variables': PAYMENT_REMINDER_VARIABLES
    },
    'PAYMENT_REMINDER_SMS_TODAY': {
        'name': 'Payment reminder - Due Today',
        'description': 'When a clients needs to pay today',
        'variables': PAYMENT_REMINDER_VARIABLES
    },
    'PAYMENT_REMINDER_SMS_PAST': {
        'name': 'Payment reminder - Was due some days ago',
        'description': 'When a client should have paid some days ago (number of days can be customized)',
        'variables': PAYMENT_REMINDER_VARIABLES
    },
    'LOAN_REPAYMENT_COMPLETED': {
        'name': 'Contract payment completed (with token)',
        'description': 'When a client complete all repayments on his loan, sent instead of Repayment made, if device activates with tokens',
        'variables': ['amount_paid', 'device_serial', 'offer_name', 'expiration_time_day', 'expiration_time_month', 'expiration_time_year',
                      'currency_sym', 'days_bought', 'days_bought_rounded', 'hours_bought', 'name', 'surname','transaction_ids', 'registration_answer_code', 'contract_reference']
    },
    'LOAN_REPAYMENT_COMPLETED_NO_TOKEN': {
        'name': 'Contract payment completed (no token)',
        'description': 'When a client complete all repayments on his loan, sent instead of Repayment made, if devices doesn not activates with tokens',
        'variables': ['amount_paid', 'device_serial', 'offer_name', 'expiration_time_day', 'expiration_time_month', 'expiration_time_year',
                      'currency_sym', 'days_bought', 'days_bought_rounded', 'hours_bought', 'name', 'surname','transaction_ids', 'contract_reference']
    },
    'LOAN_REPAYMENT_COMPLETED_UNLOCK_DISABLED': {
        'name': 'Contract payment completed (auto-unlock disabled)',
        'description': 'When a client complete all repayments on his loan, sent instead of Repayment made, if unlocking after finishing contract is disabled by the offer',
        'variables': ['amount_paid', 'device_serial', 'offer_name', 'expiration_time_day', 'expiration_time_month', 'expiration_time_year',
                      'currency_sym', 'days_bought', 'days_bought_rounded', 'hours_bought', 'name', 'surname','transaction_ids', 'contract_reference']
    },
    'AUTO_DISABLE_PAYG_SUCCESS': {
        'name': 'Disable PAYG',
        'description': 'After a client complete all his contract payments, message sent with the token to unlock the device forever',
        'variables': ['registration_answer_code', 'contract_reference']
    },
    'AUTO_DISABLE_PAYG_SUCCESS_NO_CODE': {
        'name': 'Disable PAYG (No Token)',
        'description': 'After a client complete all his contract payments, message sent for a device that has no tokens (e.g. cookstove or GSM device)',
        'variables': ['contract_reference']
    },
    'AUTO_DISABLE_PAYG_DISABLED': {
        'name': 'Call to Disable PAYG',
        'description': 'After a client complete all his contract payments, with an offer that has not been configured to send the unlock code automatically',
        'variables': []
    },
    'LOAN_OVERPAYMENT': {
        'name': 'Contract overpayment',
        'description': 'When a client pays more than is required for a contract',
        'variables': ['amount_paid', 'total_overpaid', 'total_to_pay', 'currency_sym','transaction_id']
    },
    'UNKNOWN_SENDER': {
        'name': 'Unknown sender',
        'description': 'When someone with an unknown number sends us a message',
        'variables': []
    },
    'UNKNOWN_REQUEST': {
        'name': 'Unknown Request',
        'description': 'When a client sends us a message that is not just a token request',
        'variables': []
    },
    'DEVICE_TYPE_NOT_SPECIFIED': {
        'name': 'Device type not specified',
        'description': 'When device serial specified in SMS commands or API transactions is missing the device type (prefix)',
        'variables': []
    }, 
    'CONTRACT_CANCELLED': {
        'name': 'Contract cancelled',
        'description': 'When a contract has been cancelled',
        'variables': ['name', 'surname', 'contract_reference', 'device_serial', 'offer_name']
    },
    'CONTRACT_PAUSE_SUCCESS_SMS': {
        'name': 'Contract paused SMS',
        'description': 'When a contract has been paused',
        'variables': ['name', 'surname', 'contract_reference', 'device_serial', 'offer_name', 'weeks_to_pay', 'days_to_pay', 
                        'remaining_weeks_to_pay', 'remaining_days_to_pay', 'expiration_time_day','total_to_pay', 'pending_amount','remaining_due',
                        'already_paid', 'paid_so_far+pending_amount', 'next_payment_price', 'expected_paid', 'amount_in_arrears', 'remaining_due-pending_amount']
    },
    'CONTRACT_RESUME_SUCCESS_SMS': {
        'name': 'Contract resumed SMS',
        'description': 'When a previously paused contract has been resumed',
        'variables': ['name', 'surname', 'contract_reference', 'device_serial', 'offer_name', 'weeks_to_pay', 'days_to_pay', 
                        'remaining_weeks_to_pay', 'remaining_days_to_pay', 'expiration_time_day','total_to_pay', 'pending_amount','remaining_due',
                        'already_paid', 'paid_so_far+pending_amount', 'next_payment_price', 'expected_paid', 'amount_in_arrears', 'remaining_due-pending_amount']
    }
    
}

SMS_VARIABLES_INFO = {
    'activation_answer_code': {
        'name': 'Time Token',
        'description': 'A token that adds time to the device',
        'example': '123 456 789'
    },
    'registration_answer_code': {
        'name': 'PAYG mode Token',
        'description': 'A token that sets the PAYG mode (and/or settings) of a device',
        'example': '234 567 890'
    },
    'pairing_answer_code': {
        'name': 'Pairing Code',
        'description': 'A code that pairs the device',
        'example': '123 456 789'
    },
    'expiration_time_day': {
        'name': 'Payment Due Day',
        'description': 'The day at which the next payment is due',
        'example': (datetime.now()+timedelta(weeks=1)).strftime('%d')
    },
    'expiration_time_month': {
        'name': 'Payment Due Month',
        'description': 'The month at which the next payment is due',
        'example': (datetime.now()+timedelta(weeks=1)).strftime('%m')
    },
    'expiration_time_year': {
        'name': 'Payment Due Year',
        'description': 'The year at which the next payment is due',
        'example': (datetime.now()+timedelta(weeks=1)).strftime('%Y')
    },
    'amount_paid': {
        'name': 'Amount Paid',
        'description': 'The amount paid',
        'example': 100.00
    },
    'total_overpaid': {
        'name': 'Amount Overpaid',
        'description': 'The amount overpaid',
        'example': 100.00
    },
    'currency_sym': {
        'name': '$',
        'description': 'The setup currency symbol',
        'example': '%currency_sym%'
    },
    'device_serial': {
        'name': 'Device SN',
        'description': 'The serial number of the device',
        'example': 'SOL-1234'
    },
    'offer_name': {
        'name': 'Offer Name',
        'description': 'The name of the offer',
        'example': 'Entrepreneur 80W (1 year) + 19" TV 2018'
    },
    'days_bought_rounded': {
        'name': 'Days/Months Bought (Round)',
        'description': 'The time bought rounded to the nearest day/month (based of offer)',
        'example': 6
    },
    'days_bought': {
        'name': 'Days/Months Bought (Whole)',
        'description': 'The number of full days/months bought (based on offer)',
        'example': 5
    },
    'hours_bought': {
        'name': 'Hours Bought',
        'description': 'The number of full hours bought (in addition to the full days). Use only with Days Bought (Whole)',
        'example': 17
    },
    'credit_bought': {
        'name': 'Credit Bought',
        'description': 'The amount of credit bought',
        'example': 100
    },
    'credit_unit': {
        'name': 'Credit unit',
        'description': 'The credit unit used for the offer',
        'example': 'Litres'
    },
    'weeks_paid': {
        'name': 'Weeks Paid',
        'description': 'The number of weeks paid',
        'example': 10
    },
    'days_paid': {
        'name': 'Days Paid',
        'description': 'The number of days paid (in addition to the weeks)',
        'example': 3
    },
    'weeks_to_pay': {
        'name': 'Weeks to Pay',
        'description': 'The number of total weeks to pay of the loan',
        'example': 52
    },
    'days_to_pay': {
        'name': 'Days to Pay',
        'description': 'The number of total days to pay of the loan',
        'example': 364
    },
    'remaining_weeks_to_pay': {
        'name': 'Remaining Weeks to Pay',
        'description': 'The number of weeks still left to pay of the loan',
        'example': 42
    },
    'remaining_days_to_pay': {
        'name': 'Remaining Days to Pay',
        'description': 'The number of total weeks to pay of the loan',
        'example': 294
    },
    'total_to_pay': {
        'name': 'Total Price',
        'description': 'The total amount to be paid on that contract (excl. lump-sum addons)',
        'example': 100000.00
    },
    'old_total_to_pay': {
        'name': 'Old Total Price',
        'description': 'The old total amount to be paid on that contract (excl. lump-sum addons)',
        'example': 100000.00
    },
    'total_to_pay_with_addons': {
        'name': 'Total Price (w/ all addons)',
        'description': 'The total amount to be paid on that contract including all addons',
        'example': 115000.00
    },
    'remaining_due': {
        'name': 'Remaining Due',
        'description': 'The remaining amount due to be paid (excl. lump-sum addons)',
        'example': 20000.00
    },
    'remaining_due-pending_amount': {
        'name': 'Remaining Due - Pending Amount',
        'description': 'The remaining amount due to be paid (excl. lump-sum addons) - the sum of pending reconciled payments (below the minimum)',
        'example': 18800.00
    },
    'remaining_due_with_addons': {
        'name': 'Remaining Due (w/ all addons)',
        'description': 'The remaining amount due to be paid including all addons',
        'example': 25000.00
    },
    'remaining_due_with_addons-pending_amount': {
        'name': 'Remaining Due (w/ all addons) - Pending Amount',
        'description': 'The remaining amount due to be paid including all addons - the sum of pending reconciled payments (below the minimum)',
        'example': 23800.00
    },
    'paid_so_far': {
        'name': 'Already Paid',
        'description': 'The total amount already paid on that contract (excl. lump-sum addons)',
        'example': 80000.00
    },
    'expected_paid': {
        'name': 'Expected Paid',
        'description': 'The amount expected paid so far if the client was always on time.',
        'example': 80.00
    },
    'amount_in_arrears': {
        'name': 'Amount in Arrears',
        'description': 'The amount in arrears on the loan payment.',
        'example': 10.00
    },
    'paid_so_far+pending_amount': {
        'name': 'Already Paid + Pending Amount',
        'description': 'The total amount already paid on that contract (excl. lump-sum addons) + the sum of pending reconciled payments (below the minimum)',
        'example': 81200.00
    },
    'paid_so_far_with_addons': {
        'name': 'Already Paid (w/ all addons)',
        'description': 'The total amount already paid on that contract including all addons',
        'example': 90000.00
    },
    'paid_so_far_with_addons+pending_amount': {
        'name': 'Already Paid (w/ all addons) + Pending Amount',
        'description': 'The total amount already paid on that contract including all addons + the sum of pending reconciled payments (below the minimum)',
        'example': 91200.00
    },
    'pending_amount': {
        'name': 'Pending Amount',
        'description': 'The sum of pending reconciled payments (below the minimum)',
        'example': 1200.00
    },
    'minimum_payment': {
        'name': 'Minimum Amount',
        'description': 'The minimum amount required to make the payment',
        'example': 2000.00
    },
    'commission': {
        'name': 'Commission',
        'description': 'The amount received by the agent as commission',
        'example': 120.00
    },
    'old_reference_payment': {
        'name': 'Old Reference Pricing Amount',
        'description': 'The old reference pricing amount of the contract',
        'example': 3000.00
    },
    'next_payment_price': {
        'name': 'Next Payment Price',
        'description': 'The amount expected for the next payment (same as reference pricing unless there is less than the reference pricing left to pay)',
        'example': 4000.00
    },
    'reference_payment': {
        'name': 'Reference Pricing Amount',
        'description': 'The reference pricing amount of the contract',
        'example': 4000.00
    },
    'minimum_payment-pending_amount': {
        'name': 'Remaining due for next payment ',
        'description': 'What is left to pay to reach the minimum amount to make the next payment',
        'example': 2800.00
    },
    'balance': {
        'name': 'Wallet Balance',
        'description': 'The balance on the payment wallet',
        'example': 2000.00
    },
    'amount': {
        'name': 'Amount',
        'description': 'The amount',
        'example': 100.00
    },
    'days_before_expiry': {
        'name': 'Days to Due Date',
        'description': 'The number of days before/after the next payment is/was due',
        'example': 3
    },
    'already_paid': {
        'name': 'Already paid',
        'description': 'Total amount already paid towards the downpayment or add-on payment',
        'example': 70.00
    },
    'still_to_pay': {
        'name': 'Still to pay',
        'description': 'The remaining amount to complete the downpayment',
        'example': 30.00
    },
    'remaining_to_pay': {
        'name': 'Remaining to pay',
        'description': 'The remaining amount to complete the add-on payment',
        'example': 30.00
    },
    'deposit_value': {
        'name': 'Downpayment Amount',
        'description': 'The amount of the downpayment',
        'example': 100.00
    },
    'name': {
        'name': 'Client Name',
        'description': 'The first name of the client',
        'example': 'Peter'
    },
    'surname': {
        'name': 'Client Surname',
        'description': 'The last name of the client',
        'example': 'Jakcson'
    },
    'client_phone_number': {
        'name': 'Client Phone Number',
        'description': 'The preferred phone number of the client',
        'example': '+999111222333'
    },
    'client_id': {
        'name': 'Client ID',
        'description': 'The ID of client',
        'example': '145'
    },
    'lead_id': {
        'name': 'Lead ID',
        'description': 'The ID of Lead',
        'example': '145'
    },
    'custom_id': {
        'name': '%CustomIDName%',
        'description': 'The %CustomIDName% of the client',
        'example': 'A string following the validation pattern, check the relevant setting'
    },
    'user_id': {
        'name': "User ID",
        'description': 'The ID of the user using the platform',
        'example': '3554'
    },
    'user_name': {
        'name': "User Name",
        'description': 'The name of the user using the platform',
        'example': 'Peter Jackson'
    },
    'free_time': {
        'name': 'Initial Grace Period',
        'description': 'The days of grace period before payment is due given at the beginning of the contract',
        'example': 7
    },
    'free_credit': {
        'name': 'Free Credit',
        'description': 'Free credit given at the beginning of the contract',
        'example': 7
    },
    'total_amount': {
        'name': 'Total amount',
        'description': 'The total value of the add-on sale',
        'example': 100.00
    },
    'reference_credit': {
        'name': 'Reference Credit',
        'description': 'The credit given (or time) for a reference payment',
        'example': 7
    },
    'duration': {
        'name': 'Loan Duration',
        'description': 'The total duration in days of the loan (including loan addons)',
        'example': 120
    },
    'old_duration': {
        'name': 'Old Loan Duration',
        'description': 'The old total duration in days of the loan (including loan addons)',
        'example': 100
    },
    'expected_maturity_day': {
        'name': 'Expected Maturity Day',
        'description': 'The day at which the contract should be fully repaid if the client paid according to the expected schedule',
        'example': (datetime.now()+timedelta(weeks=52)).strftime('%d')
    },
    'expected_maturity_month': {
        'name': 'Expected Maturity Month',
        'description': 'The month at which the contract should be fully repaid if the client paid according to the expected schedule',
        'example': (datetime.now()+timedelta(weeks=52)).strftime('%m')
    },
    'expected_maturity_year': {
        'name': 'Expected Maturity Year',
        'description': 'The year at which the contract should be fully repaid if the client paid according to the expected schedule',
        'example': (datetime.now()+timedelta(weeks=52)).strftime('%Y')
    },
    'reference': {
        'name': 'Add-on Reference',
        'description': 'The unique reference of the add-on',
        'example': 'C1234001-A0'
    },
    'contract_reference': {
        'name': 'Contract Reference',
        'description': 'The unique reference of the contract',
        'example': 'C1234001'
    },
    'transaction_id': {
        'name': 'Transaction ID',
        'description': 'The unique ID of the transaction (payment).',
        'example': 'MP220108.1507.G31058'
    },
    'transaction_ids': {
        'name': 'Transaction IDs',
        'description': 'The list of unique IDs of transactions linked to the same transaction (payment).',
        'example': 'MP220108.1507.G31058, MP220109.1506.G31054, MP220102.1601.G33059'
    },

}

NOT_LOGGED_PATHS = ['(.*)/static/', '/logo', '/login', '(.*).jpg$', '(.*).ico$', '/health', '(.*)/health', '/pmetrics', '(.*)/pmetrics', '(.*).js$']

ACTIVITY_LOG_BACKUP_PERIOD = 3  # backup every X months
ACTIVITY_LOG_BACKUP_MINSIZE = 100000 # number of records
ACTIVITY_LOG_BACKUP_MAXSIZE = 1000000 # number of records

BACKUP_FILE_TIME_DELAY = 60 * 5 # 5 minutes


CACHE_KEY_EXPIRY_TIME = 3600*24  # 24 hours
CONTRACT_CACHE_KEY_PREFIX = "contract_"
DEVICE_CACHE_KEY_PREFIX = "device_"
SURVEYANSWER_CACHE_KEY_PREFIX = "surveyanswer_"
CLIENT_IDS_CACHE_KEY_PREFIX = "client_ids"

HIDE_CHROME_CHECKER_COOKIE_NAME = "hide_chrome_checker"
HIDE_CHROME_CHECKER_COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # set cookie max age to one year

CONTROL_CHARS = {
    '[\u0000-\u0008\u000e-\u001a\u001c-\u001f]': '',
    '[\u0009\u00A0]': u'\u0020',
    '[\u000b\u000c]': u'\u000a',
    '&nbsp;': ' '
}

NON_PAYG_TYPE = "NPG"
NON_PAYG_IDENTIFIER = "NON_PAYG_DEVICE"

ADDONS_STATUSES_NAMES = {
    'pending': 'Pending Approval',
    'cached_unpaid': 'Pending Payment',
    'cached_paid': 'Paid',
    'delivered': 'Delivered',
    'not_delivered': 'Not Delivered',
    'onloan_not_cancelled': 'On Loan',
    'cancelled': 'Cancelled',
    'all': 'All Add-ons',
    'defaulted_not_manually_cancelled': 'Defaulted',
    'purchasing': 'Purchasing',
    'manually_cancelled': 'Manually cancelled'
}

PAYMENT_TABS = {
    'incoming': 'Received',
    'outgoing': 'Sent',
}


ADDONS_STATUSES_NAMES_ALL = ADDONS_STATUSES_NAMES.copy()
ADDONS_STATUSES_NAMES_ALL.update({
    'onloan': 'On Loan',
    'defaulted': 'Defaulted',
    'unpaid': 'Pending Payment',
    'paid': 'Paid',
})

ADDONS_TABS_CONFIG = {
    'pending': ['checkbox', 'reference', 'offer', 'client', 'contract', 'total_addon_value',
                'loan_value', 'progression', 'extension', 'note'],
    'cached_unpaid': ['checkbox', 'reference', 'offer', 'client', 'contract', 'already_paid', 'payment_source', 'total_addon_value', 'note'],
    'cached_paid': ['checkbox', 'reference', 'offer', 'client', 'contract', 'total_addon_value',
                    'payment_source', 'time_paid', 'note'],
    'delivered': ['checkbox', 'reference', 'offer', 'client', 'contract', 'quantity_sold', 'delivery_date', 'note'],
    'not_delivered': ['checkbox', 'reference', 'offer', 'client', 'contract', 'planned_delivery_date', 'note'],
    'onloan_not_cancelled': ['checkbox', 'reference', 'offer', 'client', 'contract', 'total_addon_value', 'loan_mode', 'extension', 'note', 'payment_source'],
    'cancelled': ['reference', 'offer', 'client', 'contract', 'total_addon_value', 'time_cancelled', 'canceled_by', 'note', 'extension'],
    'manually_cancelled': ['reference', 'offer', 'client', 'contract', 'total_addon_value', 'time_cancelled', 'canceled_by', 'note', 'extension'],
    'defaulted_not_manually_cancelled': ['checkbox', 'reference', 'offer', 'client', 'contract', 'quantity_sold', 'total_addon_value', 'note'],
    'purchasing':['checkbox', 'reference', 'offer', 'client', 'contract', 'total_addon_value', 'note'],
    'all': ['reference', 'offer', 'client', 'contract', 'quantity_sold', 'total_addon_value',
            'time_created', 'approved_by', 'delivery_status', 'note', 'extension'],
}


class QuickActionSettings(NamedTuple):
    name: str
    icon: str
    id: str
    statuses: List[str]
    permission: str
    extra_check: Callable[..., bool] | None = None

QUICK_ACTIONS_SETTINGS = [
    QuickActionSettings(
        'Get Token', 'offline_bolt', 'sync_activation',
        ['Active', 'Late', 'Completed', 'Overpaid'], 'SyncActivationActions',
        extra_check=lambda c: c.linked_device is not None
    ),
    QuickActionSettings(
        'Swap Device', 'import_export', 'swap_device',
        ['Active', 'Late', 'Completed', 'Paused', 'Overpaid'], 'SwapDeviceActions',
        extra_check=lambda c: c.linked_device is not None
    ),
    QuickActionSettings(
        'Give Discount', 'local_offer', 'give_discount',
        ['Active', 'Late'], 'GiveDiscountActions'
    ),
    QuickActionSettings(
        'Give Delay', 'update', 'give_delay',
        ['Active', 'Late'], 'GiveDelayActions'
    ),
    QuickActionSettings(
        'Collect Cash', 'local_atm', 'collect_cash',
        ['Active', 'Late'], 'CollectCashActions'
    ),
    QuickActionSettings(
        'Pay Client', 'mintmark', 'pay_client',
        ['Overpaid'], 'PayClientActions'
    ),
    QuickActionSettings(
        'Change Offer', 'compare_arrows', 'change_offer',
        ['Active', 'Late'], 'DoChangeOfferActions'
    ),
    QuickActionSettings(
        'Mark Defaulted', 'do_not_disturb_on', 'default',
        ['Active', 'Late'], 'MarkContractDefaultedActions'
    ),
    QuickActionSettings(
        'Undo Default', 'do_not_disturb_off', 'undo_default',
        ['Defaulted'], 'UndoContractDefaultedActions'
    ),
    QuickActionSettings(
        'Repossess Device', 'archive', 'deregister',
        ['Active', 'Late', 'Defaulted'], 'DeRegisterActions',
        extra_check=lambda c: c.linked_device is not None
    ),
    QuickActionSettings(
        'Cancel Contract', 'cancel', 'cancel',
        ['Completed', 'Active', 'Overpaid', 'Late'], 'CancelContractActions'
    ),
    QuickActionSettings(
        'Pause Contract', 'pause', 'pause',
        ['Active', 'Late'], 'PauseContractActions',
        extra_check=lambda c: not c.usage_based and not (
            c.time_based and c.offer.payment_day_of_month is not None
        )
    ),
    QuickActionSettings(
        'Resume Contract', 'resume', 'resume',
        ['Paused'], 'ResumeContractActions'
    ),
    QuickActionSettings(
        'Expected Paid', 'construction', 'expected_paid_change',
        ['Active', 'Late'], 'ChangeExpectedPaidActions'
    )
]


DEFAULT_LEAD_GENERATOR_TYPES = ['Mentor', 'Sales Leader', 'Sales Champion',
                        'Pitch Ambassador', 'Village Ambassador', 'Client', 'Super Farmer', 'Default Lead Generator']


OFFER_PROPERTIES_INFO = {
    'family': {
        'name': 'Target Use'
    },
    'no_approval_required': {
        'name': 'Approval Required',
        'macro': 'ui.no_yes'
    },
    'automatic_unlock_code_sending': {
        'name': 'Send Disable PAYG code at end of lease',
        'macro': 'ui.yes_no'
    },
    'payment_frequency': {
        'name': 'Payment Frequency',
        'macro': 'offer_macros.get_days_or_months'
    },
    'allow_pro_rata': {
        'name': 'Pro-rata allowed',
        'macro': 'ui.yes_no'
    },
    'forgive_lateness': {
        'name': 'Forgive lateness',
        'macro': 'ui.yes_no'
    },
    'registration_fee': {
        'name': 'Downpayment',
        'macro': 'ui.amount',
        'params': {'include_currency': True}
    },
    'free_credit_at_start': {
        'name': 'Free credit given at start',
        'formatter': 'format_credit'
    },
    'time_to_ownership_in_days': {
        'name': 'Loan duration',
        'formatter': 'format_credit'
    },
    'base_price_amount': {
        'name': 'Reference Pricing - Amount',
        'macro': 'ui.amount',
        'params': {'include_currency': True}
    },
    'base_price_credit': {
        'name': 'Reference Pricing - Credit',
        'formatter': 'format_credit'
    },
    'discount_price_1_amount': {
        'name': 'Discount Pricing 1 - Amount',
        'macro': 'ui.amount',
        'params': {'include_currency': True}
    },
    'discount_price_1_credit': {
        'name': 'Discount Pricing 1 - Credit',
        'formatter': 'format_credit'
    },
    'discount_price_2_amount': {
        'name': 'Discount Pricing 2 - Amount',
        'macro': 'ui.amount',
        'params': {'include_currency': True}
    },
    'discount_price_2_credit': {
        'name': 'Discount Pricing 2 - Credit',
        'formatter': 'format_credit'
    },
    'device_type': {
        'name': 'Attached device type',
        'display_func': 'get_human_readable_device_type'
    },
    'unit_cost': {
        'name': 'Raw Cost of Device',
        'macro': 'ui.amount',
        'params': {'include_currency': True}
    },
    'lighting_global_compliant': {
        'name': 'Lighting Global Approved Device',
        'macro': 'ui.yes_no'
    },
    'panel_size_in_w': {
        'name': 'Solar Panel Size',
        'macro': 'ui.suffix',
        'params': {'suffix': ' W'}
    },
    'battery_size_in_ah': {
        'name': 'Battery Size',
        'macro': 'ui.suffix',
        'params': {'suffix': ' Ah'}
    }
}

REASONS_FOR_NOT_BUYING = {
    111: 'Need to speak to family',
    112: 'Waiting for harvest',
    113: 'Waiting for other income',
    114: 'Not sure about the value of the product',
    115: 'Not sure about the value of the aftersales',
    116: 'Do not have enough trust in the warranty',
    117: 'Need to think about it',
    118: 'Thinking about a competitor',
    119: 'Too expensive for them',
    120: 'The engagement fee or downpayment is too high for them',
    121: 'The waiting time for installation is too long',
    122: 'Ready to buy'
}

MainCurrencyISOName = 'USD'

MAX_FLOAT_AMOUNT = 9999999999  # 10 digits
MAX_INT_AMOUNT = 2147483647  # 11 digits


USER_VIEWS = {
    'all': ('all_out', 'View all Users'),
    'reference_entity': ('place', 'In my reference entity'),
}

PAYMENT_VIEWS = {
    'all': ('all_out', 'View all Payments'),
    'managed_by_me': ('assignment', 'People I manage'),
    'orphaned': ('help_outline', 'Orphaned'),
}

DEVICES_VIEWS = {
    'all': ('all_out', 'View all Devices'),
    'managed_by_me': ('assignment', 'With clients I manage'),
    'orphaned': ('help_outline', 'Orphaned'),
}

CLIENT_VIEWS = {
    'all': ('all_out', 'View all Clients'),
    'managed_by_me': ('assignment', 'Managed by me'),
    'generated_by_me': ('gps_fixed', 'Generated by me')
}

LEADS_VIEWS = {
    'all': ('all_out', 'View all Leads'),
    'managed_by_me': ('assignment', 'Managed by me'),
    'generated_by_me': ('gps_fixed', 'Generated by me')
}

INTERACTION_VIEWS = {
    'all': ('all_out', 'View All Interactions'),
    'managed_by_me': ('assignment', 'Managed by me'),
    'created_by_me': ('gps_fixed', 'Created by me')
}

OVERVIEW_VIEWS = {
    'all': ('all_out', 'View All'),
    'managed_by_me': ('assignment', 'Managed by me'),
}

ISSUES_VIEWS = {
    'all': ('all_out', 'View All Issues'),
    'assigned': ('assignment', 'Assigned to me'),
    'created': ('gps_fixed', 'Created by me')
}


AVAILABLE_ICONS = ['3d_rotation', 'ac_unit', 'access_alarm', 'access_alarms', 'access_time', 'accessibility',
                   'accessible', 'account_balance', 'account_balance_wallet', 'account_box', 'account_circle',
                   'adb', 'add', 'add_a_photo', 'add_alarm', 'add_alert', 'add_box', 'add_circle', 'add_circle_outline',
                   'add_location', 'add_shopping_cart', 'add_to_photos', 'add_to_queue', 'adjust', 'airline_seat_flat',
                   'airline_seat_flat_angled', 'airline_seat_individual_suite', 'airline_seat_legroom_extra',
                   'airline_seat_legroom_normal', 'airline_seat_legroom_reduced', 'airline_seat_recline_extra',
                   'airline_seat_recline_normal', 'airplanemode_active', 'airplanemode_inactive', 'airplay',
                   'airport_shuttle', 'alarm', 'alarm_add', 'alarm_off', 'alarm_on', 'album', 'all_inclusive',
                   'all_out', 'android', 'announcement', 'apps', 'archive', 'arrow_back', 'arrow_downward', 'arrow_drop_down',
                   'arrow_drop_down_circle', 'arrow_drop_up', 'arrow_forward', 'arrow_upward', 'art_track', 'aspect_ratio',
                   'assessment', 'assignment', 'assignment_ind', 'assignment_late', 'assignment_return', 'assignment_returned',
                   'assignment_turned_in', 'assistant', 'assistant_photo', 'attach_file', 'attach_money', 'attachment',
                   'audiotrack', 'autorenew', 'av_timer', 'backspace', 'backup', 'battery_alert', 'battery_charging_full',
                   'battery_full', 'battery_std', 'battery_unknown', 'beach_access', 'beenhere', 'block', 'bluetooth',
                   'bluetooth_audio', 'bluetooth_connected', 'bluetooth_disabled', 'bluetooth_searching', 'blur_circular',
                   'blur_linear', 'blur_off', 'blur_on', 'book', 'bookmark', 'bookmark_border', 'border_all', 'border_bottom',
                   'border_clear', 'border_color', 'border_horizontal', 'border_inner', 'border_left', 'border_outer',
                   'border_right', 'border_style', 'border_top', 'border_vertical', 'branding_watermark', 'brightness_1',
                   'brightness_2', 'brightness_3', 'brightness_4', 'brightness_5', 'brightness_6', 'brightness_7',
                   'brightness_auto', 'brightness_high', 'brightness_low', 'brightness_medium', 'broken_image', 'brush',
                   'bubble_chart', 'bug_report', 'build', 'burst_mode', 'business', 'business_center', 'cached', 'cake',
                   'call', 'call_end', 'call_made', 'call_merge', 'call_missed', 'call_missed_outgoing', 'call_received',
                   'call_split', 'call_to_action', 'camera', 'camera_alt', 'camera_enhance', 'camera_front', 'camera_rear',
                   'camera_roll', 'cancel', 'card_giftcard', 'card_membership', 'card_travel', 'casino', 'cast', 'cast_connected',
                   'center_focus_strong', 'center_focus_weak', 'change_history', 'chat', 'chat_bubble', 'chat_bubble_outline',
                   'check', 'check_box', 'check_box_outline_blank', 'check_circle', 'chevron_left', 'chevron_right', 'child_care',
                   'child_friendly', 'chrome_reader_mode', 'class', 'clear', 'clear_all', 'close', 'closed_caption', 'cloud',
                   'cloud_circle', 'cloud_done', 'cloud_download', 'cloud_off', 'cloud_queue', 'cloud_upload', 'code',
                   'collections', 'collections_bookmark', 'color_lens', 'colorize', 'comment', 'compare', 'compare_arrows',
                   'computer', 'confirmation_number', 'contact_mail', 'contact_phone', 'contacts', 'content_copy', 'content_cut',
                   'content_paste', 'control_point', 'control_point_duplicate', 'copyright', 'create', 'create_new_folder',
                   'credit_card', 'crop', 'crop_16_9', 'crop_3_2', 'crop_5_4', 'crop_7_5', 'crop_din', 'crop_free', 'crop_landscape',
                   'crop_original', 'crop_portrait', 'crop_rotate', 'crop_square', 'dashboard', 'data_usage', 'date_range', 'dehaze',
                   'delete', 'delete_forever', 'delete_sweep', 'description', 'desktop_mac', 'desktop_windows', 'details', 'developer_board',
                   'developer_mode', 'device_hub', 'devices', 'devices_other', 'dialer_sip', 'dialpad', 'directions', 'directions_bike',
                   'directions_boat', 'directions_bus', 'directions_car', 'directions_railway', 'directions_run', 'directions_subway',
                   'directions_transit', 'directions_walk', 'disc_full', 'dns', 'do_not_disturb', 'do_not_disturb_alt', 'do_not_disturb_off',
                   'do_not_disturb_on', 'dock', 'domain', 'done', 'done_all', 'donut_large', 'donut_small', 'drafts', 'drag_handle',
                   'drive_eta', 'dvr', 'edit', 'edit_location', 'eject', 'email', 'enhanced_encryption', 'equalizer', 'error',
                   'error_outline', 'euro_symbol', 'ev_station', 'event', 'event_available', 'event_busy', 'event_note', 'event_seat',
                   'exit_to_app', 'expand_less', 'expand_more', 'explicit', 'explore', 'exposure', 'exposure_neg_1', 'exposure_neg_2',
                   'exposure_plus_1', 'exposure_plus_2', 'exposure_zero', 'extension', 'face', 'fast_forward', 'fast_rewind',
                   'favorite', 'favorite_border', 'featured_play_list', 'featured_video', 'feedback', 'fiber_dvr', 'fiber_manual_record',
                   'fiber_new', 'fiber_pin', 'fiber_smart_record', 'file_download', 'file_upload', 'filter', 'filter_1', 'filter_2',
                   'filter_3', 'filter_4', 'filter_5', 'filter_6', 'filter_7', 'filter_8', 'filter_9', 'filter_9_plus', 'filter_b_and_w',
                   'filter_center_focus', 'filter_drama', 'filter_frames', 'filter_hdr', 'filter_list', 'filter_none', 'filter_tilt_shift',
                   'filter_vintage', 'find_in_page', 'find_replace', 'fingerprint', 'first_page', 'fitness_center', 'flag', 'flare',
                   'flash_auto', 'flash_off', 'flash_on', 'flight', 'flight_land', 'flight_takeoff', 'flip', 'flip_to_back', 'flip_to_front',
                   'folder', 'folder_open', 'folder_shared', 'folder_special', 'font_download', 'format_align_center', 'format_align_justify',
                   'format_align_left', 'format_align_right', 'format_bold', 'format_clear', 'format_color_fill', 'format_color_reset',
                   'format_color_text', 'format_indent_decrease', 'format_indent_increase', 'format_italic', 'format_line_spacing',
                   'format_list_bulleted', 'format_list_numbered', 'format_paint', 'format_quote', 'format_shapes', 'format_size',
                   'format_strikethrough', 'format_textdirection_l_to_r', 'format_textdirection_r_to_l', 'format_underlined', 'forum',
                   'forward', 'forward_10', 'forward_30', 'forward_5', 'free_breakfast', 'fullscreen', 'fullscreen_exit', 'functions',
                   'g_translate', 'gamepad', 'games', 'gavel', 'gesture', 'get_app', 'gif', 'golf_course', 'gps_fixed', 'gps_not_fixed',
                   'gps_off', 'grade', 'gradient', 'grain', 'graphic_eq', 'grid_off', 'grid_on', 'group', 'group_add', 'group_work',
                   'hd', 'hdr_off', 'hdr_on', 'hdr_strong', 'hdr_weak', 'headset', 'headset_mic', 'healing', 'hearing', 'help',
                   'help_outline', 'high_quality', 'highlight', 'highlight_off', 'history', 'home', 'hot_tub', 'hotel', 'hourglass_empty',
                   'hourglass_full', 'http', 'https', 'image', 'image_aspect_ratio', 'import_contacts', 'import_export', 'important_devices',
                   'inbox', 'indeterminate_check_box', 'info', 'info_outline', 'input', 'insert_chart', 'insert_comment', 'insert_drive_file',
                   'insert_emoticon', 'insert_invitation', 'insert_link', 'insert_photo', 'invert_colors', 'invert_colors_off', 'iso',
                   'keyboard', 'keyboard_arrow_down', 'keyboard_arrow_left', 'keyboard_arrow_right', 'keyboard_arrow_up', 'keyboard_backspace',
                   'keyboard_capslock', 'keyboard_hide', 'keyboard_return', 'keyboard_tab', 'keyboard_voice', 'kitchen', 'label',
                   'label_outline', 'landscape', 'language', 'laptop', 'laptop_chromebook', 'laptop_mac', 'laptop_windows', 'last_page',
                   'launch', 'layers', 'layers_clear', 'leak_add', 'leak_remove', 'lens', 'library_add', 'library_books', 'library_music',
                   'lightbulb_outline', 'line_style', 'line_weight', 'linear_scale', 'link', 'linked_camera', 'list', 'live_help', 'live_tv',
                   'local_activity', 'local_airport', 'local_atm', 'local_bar', 'local_cafe', 'local_car_wash', 'local_convenience_store',
                   'local_dining', 'local_drink', 'local_florist', 'local_gas_station', 'local_grocery_store', 'local_hospital', 'local_hotel',
                   'local_laundry_service', 'local_library', 'local_mall', 'local_movies', 'local_offer', 'local_parking', 'local_pharmacy',
                   'local_phone', 'local_pizza', 'local_play', 'local_post_office', 'local_printshop', 'local_see', 'local_shipping',
                   'local_taxi', 'location_city', 'location_disabled', 'location_off', 'location_on', 'location_searching', 'lock',
                   'lock_open', 'lock_outline', 'looks', 'looks_3', 'looks_4', 'looks_5', 'looks_6', 'looks_one', 'looks_two', 'loop',
                   'loupe', 'low_priority', 'loyalty', 'mail', 'mail_outline', 'map', 'markunread', 'markunread_mailbox', 'memory', 'menu',
                   'merge_type', 'message', 'mic', 'mic_none', 'mic_off', 'mms', 'mode_comment', 'mode_edit', 'monetization_on', 'money_off',
                   'monochrome_photos', 'mood', 'mood_bad', 'more', 'more_horiz', 'more_vert', 'motorcycle', 'mouse', 'move_to_inbox',
                   'movie', 'movie_creation', 'movie_filter', 'multiline_chart', 'music_note', 'music_video', 'my_location', 'nature',
                   'nature_people', 'navigate_before', 'navigate_next', 'navigation', 'near_me', 'network_cell', 'network_check',
                   'network_locked', 'network_wifi', 'new_releases', 'next_week', 'nfc', 'no_encryption', 'no_sim', 'not_interested',
                   'note', 'note_add', 'notifications', 'notifications_active', 'notifications_none', 'notifications_off',
                   'notifications_paused', 'offline_pin', 'ondemand_video', 'opacity', 'open_in_browser', 'open_in_new', 'open_with',
                   'pages', 'pageview', 'palette', 'pan_tool', 'panorama', 'panorama_fish_eye', 'panorama_horizontal', 'panorama_vertical',
                   'panorama_wide_angle', 'party_mode', 'pause', 'pause_circle_filled', 'pause_circle_outline', 'payment', 'people',
                   'people_outline', 'perm_camera_mic', 'perm_contact_calendar', 'perm_data_setting', 'perm_device_information',
                   'perm_identity', 'perm_media', 'perm_phone_msg', 'perm_scan_wifi', 'person', 'person_add', 'person_outline', 'person_pin',
                   'person_pin_circle', 'personal_video', 'pets', 'phone', 'phone_android', 'phone_bluetooth_speaker', 'phone_forwarded',
                   'phone_in_talk', 'phone_iphone', 'phone_locked', 'phone_missed', 'phone_paused', 'phonelink', 'phonelink_erase',
                   'phonelink_lock', 'phonelink_off', 'phonelink_ring', 'phonelink_setup', 'photo', 'photo_album', 'photo_camera',
                   'photo_filter', 'photo_library', 'photo_size_select_actual', 'photo_size_select_large', 'photo_size_select_small',
                   'picture_as_pdf', 'picture_in_picture', 'picture_in_picture_alt', 'pie_chart', 'pie_chart_outlined', 'pin_drop',
                   'place', 'play_arrow', 'play_circle_filled', 'play_circle_outline', 'play_for_work', 'playlist_add', 'playlist_add_check',
                   'playlist_play', 'plus_one', 'poll', 'polymer', 'pool', 'portable_wifi_off', 'portrait', 'power', 'power_input',
                   'power_settings_new', 'pregnant_woman', 'present_to_all', 'print', 'priority_high', 'public', 'publish', 'query_builder',
                   'question_answer', 'queue', 'queue_music', 'queue_play_next', 'radio', 'radio_button_checked', 'radio_button_unchecked',
                   'rate_review', 'receipt', 'recent_actors', 'record_voice_over', 'redeem', 'redo', 'refresh', 'remove', 'remove_circle',
                   'remove_circle_outline', 'remove_from_queue', 'remove_red_eye', 'remove_shopping_cart', 'reorder', 'repeat', 'repeat_one',
                   'replay', 'replay_10', 'replay_30', 'replay_5', 'reply', 'reply_all', 'report', 'report_problem', 'restaurant',
                   'restaurant_menu', 'restore', 'restore_page', 'ring_volume', 'room', 'room_service', 'rotate_90_degrees_ccw',
                   'rotate_left', 'rotate_right', 'rounded_corner', 'router', 'rowing', 'rss_feed', 'rv_hookup', 'satellite', 'save',
                   'scanner', 'schedule', 'school', 'screen_lock_landscape', 'screen_lock_portrait', 'screen_lock_rotation',
                   'screen_rotation', 'screen_share', 'sd_card', 'sd_storage', 'search', 'security', 'select_all', 'send',
                   'sentiment_dissatisfied', 'sentiment_neutral', 'sentiment_satisfied', 'sentiment_very_dissatisfied',
                   'sentiment_very_satisfied', 'settings', 'settings_applications', 'settings_backup_restore', 'settings_bluetooth',
                   'settings_brightness', 'settings_cell', 'settings_ethernet', 'settings_input_antenna', 'settings_input_component',
                   'settings_input_composite', 'settings_input_hdmi', 'settings_input_svideo', 'settings_overscan', 'settings_phone',
                   'settings_power', 'settings_remote', 'settings_system_daydream', 'settings_voice', 'share', 'shop', 'shop_two',
                   'shopping_basket', 'shopping_cart', 'short_text', 'show_chart', 'shuffle', 'signal_cellular_4_bar',
                   'signal_cellular_connected_no_internet_4_bar', 'signal_cellular_no_sim', 'signal_cellular_null', 'signal_cellular_off',
                   'signal_wifi_4_bar', 'signal_wifi_4_bar_lock', 'signal_wifi_off', 'sim_card', 'sim_card_alert', 'skip_next',
                   'skip_previous', 'slideshow', 'slow_motion_video', 'smartphone', 'smoke_free', 'smoking_rooms', 'sms', 'sms_failed',
                   'snooze', 'sort', 'sort_by_alpha', 'spa', 'space_bar', 'speaker', 'speaker_group', 'speaker_notes', 'speaker_notes_off',
                   'speaker_phone', 'spellcheck', 'star', 'star_border', 'star_half', 'stars', 'stay_current_landscape',
                   'stay_current_portrait', 'stay_primary_landscape', 'stay_primary_portrait', 'stop', 'stop_screen_share',
                   'storage', 'store', 'store_mall_directory', 'straighten', 'streetview', 'strikethrough_s', 'style',
                   'subdirectory_arrow_left', 'subdirectory_arrow_right', 'subject', 'subscriptions', 'subtitles', 'subway',
                   'supervisor_account', 'surround_sound', 'swap_calls', 'swap_horiz', 'swap_vert', 'swap_vertical_circle',
                   'switch_camera', 'switch_video', 'sync', 'sync_disabled', 'sync_problem', 'system_update', 'system_update_alt',
                   'tab', 'tab_unselected', 'tablet', 'tablet_android', 'tablet_mac', 'tag_faces', 'tap_and_play', 'terrain',
                   'text_fields', 'text_format', 'textsms', 'texture', 'theaters', 'thumb_down', 'thumb_up', 'thumbs_up_down',
                   'time_to_leave', 'timelapse', 'timeline', 'timer', 'timer_10', 'timer_3', 'timer_off', 'title', 'toc', 'today',
                   'toll', 'tonality', 'touch_app', 'toys', 'track_changes', 'traffic', 'train', 'tram', 'transfer_within_a_station',
                   'transform', 'translate', 'trending_down', 'trending_flat', 'trending_up', 'tune', 'turned_in', 'turned_in_not',
                   'tv', 'unarchive', 'undo', 'unfold_less', 'unfold_more', 'update', 'usb', 'verified_user', 'vertical_align_bottom',
                   'vertical_align_center', 'vertical_align_top', 'vibration', 'video_call', 'video_label', 'video_library', 'videocam',
                   'videocam_off', 'videogame_asset', 'view_agenda', 'view_array', 'view_carousel', 'view_column', 'view_comfy',
                   'view_compact', 'view_day', 'view_headline', 'view_list', 'view_module', 'view_quilt', 'view_stream', 'view_week',
                   'vignette', 'visibility', 'visibility_off', 'voice_chat', 'voicemail', 'volume_down', 'volume_mute', 'volume_off',
                   'volume_up', 'vpn_key', 'vpn_lock', 'wallpaper', 'warning', 'watch', 'watch_later', 'wb_auto', 'wb_cloudy',
                   'wb_incandescent', 'wb_iridescent', 'wb_sunny', 'wc', 'web', 'web_asset', 'weekend', 'whatshot', 'widgets',
                   'wifi', 'wifi_lock', 'wifi_tethering', 'work', 'wrap_text', 'youtube_searched_for', 'zoom_in', 'zoom_out', 'zoom_out_map'] + new_icons



qtypes = [
    (1,'yes/no'),(2,'text'),(3,'numeric', {'unit': 'minutes'}),
    (4,'choice_text', {'choices': [{'order': 1,'value': 'Super'}, {'order': 2,'value': 'Mega'}, {'order': 3,'value': 'Giga'}]}), 
    (5,'choice_numeric', {'choices': [{'order': 1,'value': 5}, {'order': 2,'value': 10}, {'order': 3,'value': 15}]}),
    (6,'picture'),(7,'long_text'),(8,'checkbox'),(9,'date'),
    (10,'note',{'full_question': "This is a note with **markdown** and [links](https://www.paygops.com/)"}),
    (11,'gps'),(12,'url'),(13,'signature')
]

simple_tquestions = []
for qtype in qtypes:
    tq = {
        'type': qtype[0],
        'name': f'{qtype[1].capitalize()} Question',
        'full_question': f"What's the {qtype[1]}?",
        'icon': 'smartphone'
    }
    if len(qtype) > 2:
        tq.update(qtype[2])
    simple_tquestions.append(tq)

complex_tquestions = []
for qtype in qtypes:
    multi = qtype[1] not in ['yes/no', 'checkbox', 'note']
    value = qtype[1] not in ['yes/no', 'checkbox', 'note', 'date', 'signature', 'picture']
    tq = {
        'type': qtype[0],
        'name': f'{qtype[1].capitalize()} Question',
        'full_question': f"What are the {qtype[1]}?",
        'icon': 'key',
        'minValue': 10 if value else None,
        'maxValue': 50 if value else None,
        'min_answers': 2 if multi else (1 if qtype[1] not in 'note' else 0),
        'max_answers': 5 if multi else 1,
    }
    if len(qtype) > 2:
        tq.update(qtype[2])
    complex_tquestions.append(tq)

TEST_SURVEYS_INFO = [{
        'name': 'Simple Test Survey',
        'icon': 'map',
        'for_clients': True,
        'for_leads': True,
        'questions': simple_tquestions
    },
    {
        'name': 'Complex Test Survey',
        'icon': 'favorite',
        'for_clients': True,
        'for_leads': True,
        'questions': complex_tquestions
    },
]


SYSTEM_SURVEYS_INFO = [{
    'name': 'Phone Charging Review',
    'icon': '',
    'for_clients': False,
    'for_leads': False,
    'questions': [{
        'type': 3,
        'name': 'Charges since last',
        'full_question': 'Charges Since Last Visit',
        'icon': 'smartphone'
    }, {
        'type': 3,
        'name': 'Turnover since last',
        'full_question': 'Turnover Since Last Visit',
        'icon': 'attach_money'
    }]
}, {
    'name': 'General Discussion',
    'icon': '',
    'for_clients': False,
    'for_leads': False,
    'questions': [{
        'type': 7,
        'name': 'Issues faced',
        'full_question': 'Issues faced',
        'icon': 'assignment_late',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Main recommendations given',
        'full_question': 'Main recommendations given',
        'icon': 'chat_bubble',
        'min_answers': 1
    }]
}, {
    'name': 'Installation',
    'icon': '',
    'for_clients': False,
    'for_leads': False,
    'questions': [{
        'type': 3,
        'name': 'Time to perform installation',
        'full_question': 'How long did it take to install (from arrival to departure)?',
        'icon': 'schedule',
        'unit': 'minutes',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Issues faced during installation',
        'full_question': 'What were the main challenges during this installation?',
        'icon': 'assignment_late',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Recommendations given during installation',
        'full_question': 'What recommendations did I give to the client during installation?',
        'icon': 'chat_bubble',
        'min_answers': 1
    }, {
        'type': 3,
        'name': 'Number of people trained during installation',
        'full_question': 'How many neighbours, children, friends have you trained to activate?',
        'icon': 'stay_current_portrait',
        'min_answers': 1
    }, {
        'type': 8,
        'name': 'I gave the Company phone number',
        'full_question': 'I gave the client the Company phone number'
    }, {
        'type': 8,
        'name': 'Took a photo of client',
        'full_question': 'I took a picture of the client (including GPS)'
    }, {
        'type': 8,
        'name': 'Put spray on battery',
        'full_question': 'I put spray on the battery'
    }, {
        'type': 8,
        'name': 'Gave an activation sticker',
        'full_question': 'I gave a sticker about activation to the client'
    }, {
        'type': 8,
        'name': 'Gave a tampering sticker',
        'full_question': 'I gave a sticker about tampering to the client'
    }, {
        'type': 8,
        'name': 'Informed about offers',
        'full_question': 'I informed the client of our special offers'
    }, {
        'type': 8,
        'name': 'Informed about referral',
        'full_question': 'I informed the client that he can get free energy by helping find new customers'
    }, {
        'type': 0,
        'name': 'battery_group_installation',
        'full_question': 'Battery',
        'icon': 'work',
        'max_answers': 1,
        'min_answers': 0,
        'sub_questions': [{
            'type': 2,
            'name': 'Installation Battery Swap 1',
            'full_question': 'Battery serial number',
            'icon': 'battery_alert',
            'min_answers': 1
        }, {
            'type': 2,
            'name': 'Installation Battery Swap 2',
            'full_question': 'Battery #2 serial number (if any)',
            'icon': 'battery_alert'
        }, {
            'type': 2,
            'name': 'Installation Battery Swap 3',
            'full_question': 'Battery #3 serial number (if any)',
            'icon': 'battery_alert'
        }]
    }]
}, {
    'name': 'Upgrade',
    'icon': '',
    'for_clients': False,
    'for_leads': False,
    'questions': [{
        'type': 2,
        'name': 'Type of upgrade',
        'full_question': 'What type of upgrade was it?',
        'icon': 'assignment_late',
        'min_answers': 1
    }, {
        'type': 2,
        'name': 'Old Offer Upgrade',
        'full_question': 'Old Offer Upgrade',
        'icon': 'add_shopping_cart',
        'min_answers': 1
    }, {
        'type': 3,
        'name': 'Time to perform upgrade',
        'full_question': 'How long did it take to upgrade (from arrival to departure)?',
        'icon': 'schedule',
        'unit': 'minutes',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Challenges faced during upgrade',
        'full_question': 'What were the main challenges during this installation?',
        'icon': 'assignment_late',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Recommendations given during upgrade',
        'full_question': 'What recommendations did I give to the client during installation?',
        'icon': 'chat_bubble',
        'min_answers': 1
    }, {
        'type': 3,
        'name': 'Number of people trained during upgrade',
        'full_question': 'How many neighbours, children, friends have you trained to activate?',
        'icon': 'stay_current_portrait',
        'min_answers': 1
    }, {
        'type': 8,
        'name': 'I gave the Company phone number upgrade',
        'full_question': 'I gave the client the Company phone number'
    }, {
        'type': 8,
        'name': 'Took a photo of client upgrade',
        'full_question': 'I took a picture of the client (including GPS)'
    }, {
        'type': 8,
        'name': 'Put spray on battery upgrade',
        'full_question': 'I put spray on the battery'
    }, {
        'type': 8,
        'name': 'Gave an activation sticker upgrade',
        'full_question': 'I gave a sticker about activation to the client'
    }, {
        'type': 8,
        'name': 'Gave a tampering sticker upgrade',
        'full_question': 'I gave a sticker about tampering to the client'
    }, {
        'type': 8,
        'name': 'Informed about offers upgrade',
        'full_question': 'I informed the client of our special offers'
    }, {
        'type': 8,
        'name': 'Informed about referral upgrade',
        'full_question': 'I informed the client that he can get free energy by helping find new customers'
    }]
}, {
    'name': 'Downgrade',
    'icon': '',
    'for_clients': False,
    'for_leads': False,
    'questions': [{
        'type': 3,
        'name': 'Time to perform downgrade',
        'full_question': 'How long did it take to downgrade (from arrival to departure)?',
        'icon': 'schedule',
        'unit': 'minutes',
        'min_answers': 1
    }, {
        'type': 2,
        'name': 'Old Offer Downgrade',
        'full_question': 'Old Offer Downgrade',
        'icon': 'add_shopping_cart',
        'min_answers': 1
    }, {
        'type': 2,
        'name': 'New Offer Downgrade',
        'full_question': 'New Offer Downgrade',
        'icon': 'add_shopping_cart',
        'min_answers': 1
    }, {
        'type': 3,
        'name': 'Number of people trained during downgrade',
        'full_question': 'How many neighbours, children, friends have you trained to activate?',
        'icon': 'stay_current_portrait',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Issues faced during downgrade',
        'full_question': 'What were the main challenges during this downgrade?',
        'icon': 'assignment_late',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Reason for downgrade',
        'full_question': 'For what reason the client want to downgrade?',
        'icon': 'chat_bubble',
        'min_answers': 1
    }]
}, {
    'name': 'Uninstallation',
    'icon': '',
    'for_clients': False,
    'for_leads': False,
    'questions': [{
        'type': 3,
        'name': 'Time to perform uninstallation',
        'full_question': 'How long did it take to uninstall (from arrival to departure)?',
        'icon': 'schedule',
        'unit': 'minutes',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Challenges faced during uninstallation',
        'full_question': 'What were the main challenges during this uninstallation?',
        'icon': 'assignment_late',
        'min_answers': 1
    }, {
        'type': 4,
        'name': 'Main reasons for uninstallation',
        'full_question': 'For what reason the client stopped using Solaris? (max. 3)',
        'icon': 'chat_bubble',
        'min_answers': 1,
        'max_answers': 3,
        'choices': [{
            'order': 1,
            'value': 'Too expensive'
        }, {
            'order': 2,
            'value': 'Got connected to the grid'
        }, {
            'order': 3,
            'value': 'Financial issue'
        }, {
            'order': 4,
            'value': 'Too expensive'
        }, {
            'order': 5,
            'value': 'Family issue'
        }, {
            'order': 6,
            'value': 'Moving'
        }, {
            'order': 7,
            'value': 'Death'
        }, {
            'order': 8,
            'value': 'Tampering issue'
        }, {
            'order': 9,
            'value': 'Payment issue'
        }, {
            'order': 10,
            'value': 'Too many technical issues'
        }, {
            'order': 11,
            'value': 'Other'
        }]
    }, {
        'type': 7,
        'name': 'Reason for uninstallation details',
        'full_question': 'For what reason the client stopped using Solaris?',
        'icon': 'chat_bubble',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Alternative lighting method',
        'full_question': 'What method of lighting is the client now going to use?',
        'icon': 'lightbulb_outline',
        'min_answers': 1
    }]
}, {
    'name': 'Remind to pay',
    'icon': '',
    'for_clients': False,
    'for_leads': False,
    'questions': [{
        'type': 4,
        'name': 'Reason for late payment',
        'full_question': 'Why did the client not pay on time?',
        'icon': 'alarm',
        'min_answers': 1,
        'max_answers': 0,
        'choices': [{
            'order': 1,
            'value': 'Not received his salary on time'
        }, {
            'order': 2,
            'value': 'Low price of crops',
        }, {
            'order': 3,
            'value': 'Waiting to sell crops',
        }, {
            'order': 4,
            'value': 'No regular income',
        }, {
            'order': 5,
            'value': 'Forgot to pay',
        }, {
            'order': 6,
            'value': 'Forgot to send code',
        }, {
            'order': 7,
            'value': 'Does not know or forgot how to activate at all',
        }, {
            'order': 8,
            'value': 'Cannot activate because he/she struggle to read',
        }, {
            'order': 9,
            'value': 'Away from home',
        }, {
            'order': 10,
            'value': 'Problem with Mobile Money',
        }, {
            'order': 11,
            'value': 'No Mobile Money agent in the village',
        }, {
            'order': 12,
            'value': 'Lost his phone or SIM card',
        }, {
            'order': 13,
            'value': 'No contract',
        }, {
            'order': 14,
            'value': 'Device locked',
        }, {
            'order': 15,
            'value': 'Sick relatives',
        }, {
            'order': 16,
            'value': 'Family issues',
        }, {
            'order': 17,
            'value': 'Other (fill explanation below)'
        }]
    }, {
        'type': 7,
        'name': 'Details on the late payment',
        'full_question': 'Details on the late payment',
        'icon': 'assignment_late',
    }, {
        'type': 2,
        'name': 'Alternative lighting technology',
        'full_question': 'What alternative does the client use?',
        'icon': 'lightbulb_outline',
    }, {
        'type': 3,
        'name': 'Promise to pay',
        'full_question': 'When did the client promised to pay if he did?',
        'icon': 'alarm',
        'unit': 'days'
    }, {
        'type': 7,
        'name': 'Recommendations Given Late Payment',
        'full_question': 'Recommendations Given',
        'icon': 'chat_bubble'
    }]
}, {
    'name': 'Business follow-up',
    'icon': '',
    'for_clients': False,
    'for_leads': False,
    'questions': [{
        'type': 7,
        'name': 'Main actions followup',
        'full_question': 'Main actions followup',
        'icon': '',
        'min_answers': 1
    }, {
        'type': 3,
        'name': 'Number of phones charged',
        'full_question': 'Number of phones charged',
        'icon': '',
        'min_answers': 1
    }, {
        'type': 3,
        'name': 'Number of haircuts given',
        'full_question': 'Number of haircuts given',
        'icon': '',
        'min_answers': 1
    }, {
        'type': 3,
        'name': 'Turnover since last visit',
        'full_question': 'Turnover since last visit',
        'icon': '',
        'min_answers': 1
    }, {
        'type': 4,
        'name': 'Turnover trend',
        'full_question': 'Turnover trend',
        'icon': '',
        'choices': [{
            'order': 1,
            'value': 'Lowering'
        }, {
            'order': 2,
            'value': 'Steady',
        }, {
            'order': 3,
            'value': 'Rising',
        }]
    }, {
        'type': 7,
        'name': 'Client Training followup Actions required',
        'full_question': 'What does the client needs to do before the next visit?',
        'icon': '',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Mentor Training followup Actions required',
        'full_question': 'What do I need to do before the next visit?',
        'icon': '',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Followup observations',
        'full_question': 'Followup observations',
        'icon': ''
    }]
}, {
    'name': 'Business training assessment',
    'icon': '',
    'for_clients': False,
    'for_leads': False,
    'questions': [{
        'type': 2,
        'name': 'Type of trained business',
        'full_question': 'What is the type of the business',
        'icon': '',
        'min_answers': 1
    }, {
        'type': 2,
        'name': 'Training priority #1',
        'full_question': 'What is the #1 training priority?',
        'icon': '',
        'min_answers': 1
    }, {
        'type': 2,
        'name': 'Training priority #2',
        'full_question': 'What is the #2 training priority?',
        'icon': '',
        'min_answers': 1
    }, {
        'type': 2,
        'name': 'Training priority #3',
        'full_question': 'What is the #3 training priority?',
        'icon': '',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Training assessment Other observations',
        'full_question': 'Other observations about the Client (e.g. the entrepreneur has a great potential to improve quickly)',
        'icon': ''
    }, {
        'type': 2,
        'name': 'Next Visit Topic training',
        'full_question': 'What will be the topic of the next visit? (e.g. checking that inventory is filled + marketing empowerement)',
        'icon': '',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Training assessment Actions required',
        'full_question': 'What do I need to do before the next visit?',
        'min_answers': 1,
        'icon': ''
    }]
}, {
    'name': 'Business training',
    'icon': '',
    'for_clients': False,
    'for_leads': False,
    'questions': [{
        'type': 2,
        'name': 'Training topic',
        'full_question': 'Topic of the training',
        'icon': '',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Main training difficulties',
        'full_question': 'Main training difficulties',
        'icon': ''
    }, {
        'type': 7,
        'name': 'Training Actions required',
        'full_question': 'What does the client need to do before the next visit? (e.g. show me that he filled the inventory checklist on a weekly basis)',
        'min_answers': 1,
        'icon': ''
    }, {
        'type': 7,
        'name': 'Training other observations',
        'full_question': 'Other observations about the client (e.g. the client has a great potential to improve quickly)',
        'icon': ''
    }]
}, {
    'name': 'Business mentorship',
    'icon': '',
    'for_clients': False,
    'for_leads': False,
    'questions': [{
        'type': 0,
        'name': 'Business Issue',
        'full_question': '',
        'icon': 'work',
        'max_answers': 10,
        'min_answers': 1,
        'sub_questions': [{
            'type': 7,
            'name': 'Detailed Business Issue',
            'full_question': 'What is the encountered issue? (e.g. does not have proper inventory)',
            'icon': '',
            'min_answers': 1
        }, {
            'type': 7,
            'name': 'Business Actions required',
            'full_question': 'What does the client need to do before the next visit? (e.g. show me that he filled the inventory checklist on a weekly basis)',
            'icon': '',
            'min_answers': 1
        }, {
            'type': 7,
            'name': 'Business Advice',
            'full_question': 'What help did I gave her/him? (e.g. I gave him an inventory checklist and we filled together all the items in his shop)',
            'icon': '',
            'min_answers': 1
        }]
    }, {
        'type': 7,
        'name': 'Business Other observations',
        'full_question': 'Other observations about the Client (e.g. the entrepreneur has a great potential to improve quickly)',
        'icon': ''
    }, {
        'type': 2,
        'name': 'Next Visit Topic',
        'full_question': 'What will be the topic of the next visit? (e.g. checking that inventory is filled + marketing empowerement)',
        'min_answers': 1,
        'icon': ''
    }]
}, {
    'name': 'Support in Activation',
    'icon': '',
    'for_clients': False,
    'for_leads': False,
    'questions': [{
        'type': 7,
        'name': 'Main Activation Issue',
        'full_question': 'Main Activation Issue',
        'icon': 'assignment_late',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Other recommendations',
        'full_question': 'Other recommendations',
        'icon': 'chat_bubble',
        'min_answers': 1
    }, {
        'type': 3,
        'name': 'Number of people trained during support',
        'full_question': 'How many neighbours, children, friends have you trained to activate?',
        'icon': 'stay_current_portrait',
        'min_answers': 1
    }, {
        'type': 8,
        'name': 'Gave an activation sticker during support',
        'full_question': 'I gave a sticker about activation to the client'
    }]
}, {
    'name': 'Friendly Talk',
    'icon': '',
    'for_clients': False,
    'for_leads': False,
    'questions': [{
        'type': 7,
        'name': 'Discussion Summary',
        'full_question': 'Discussion Summary',
        'icon': 'chat_bubble',
    }]
}, {
    'name': 'System Issue',
    'icon': 'error',
    'for_clients': False,
    'for_leads': False,
    'questions': [{
        'type': 7,
        'name': 'System Issue Description',
        'full_question': 'What is the issue in one sentence?',
        'icon': 'assignment_late',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'System Issue Additional Details',
        'full_question': 'More details about the problem.',
        'icon': 'description',
        'min_answers': 1
    }, {
        'type': 3,
        'name': 'Device Serial Number',
        'full_question': 'Device Serial Number',
        'icon': '',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Customer behaviour before issue',
        'full_question': 'What was the customer doing when the problem occured? (using lights, charging phones, etc.)',
        'icon': 'description',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Usage in days before issue',
        'full_question': 'What was the usage in the days before? (number of phone charged, hours of lights etc.)',
        'icon': 'trending_up',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Weather in days before issue',
        'full_question': 'How was the weather in the last few days? (Hot/cold, cloudy/sunny/rainy, normal?)',
        'icon': 'wb_cloudy',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Warning messages',
        'full_question': 'Were there any warning messages on the device? (Low battery, port cannot turn on, etc.)',
        'icon': 'sms_failed',
        'min_answers': 1
    }, {
        'type': 1,
        'name': 'Device is still usable',
        'full_question': 'Can the device still be used?',
        'min_answers': 1
    }, {
        'type': 1,
        'name': 'Sign of Tampering',
        'full_question': 'Were there sign of tampering?',
        'icon': 'pan_tool',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Tampering Check',
        'full_question': 'How did you check the tampering? Was the terminal painted?',
        'icon': 'pan_tool',
    }, {
        'type': 7,
        'name': 'System Issue Solutions',
        'full_question': 'What are the next steps to solve the issue (planned or already done)?',
        'icon': 'description',
        'min_answers': 1
    }]
}, {
    'name': 'System Issue Details',
    'icon': 'error',
    'for_clients': False,
    'for_leads': False,
    'questions': [{
        'type': 7,
        'name': 'System Issue New Details',
        'full_question': 'New details about the problem.',
        'icon': 'description',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Problem source',
        'full_question': 'Does the problem seem to be with the device, battery, panel, cabling or unknown?',
        'icon': '',
    }, {
        'type': 7,
        'name': 'Permanent damage',
        'full_question': 'Is there any permanent damage to the device, battery or panel?',
        'icon': '',
    }, {
        'type': 3,
        'name': 'Device Serial Number',
        'full_question': 'Device Serial Number',
        'icon': '',
        'min_answers': 1
    }, {
        'type': 1,
        'name': 'Charging issue',
        'full_question': 'Is it a charging issue?',
        'icon': 'battery_unknown',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Menu reading',
        'full_question': 'What does the mentor menu for charging read? (Bat Voltage, Bat Current, Panel Voltage, Panel Current)',
        'icon': 'battery_charging_full',
    }, {
        'type': 2,
        'name': 'Battery Voltage',
        'full_question': 'With a multimeter, measure voltage at battery terminal (while still connected to the device)',
        'icon': 'battery_unknown'
    }, {
        'type': 2,
        'name': 'Battery Current',
        'full_question': 'With a multimeter, measure current flowing from the device.',
        'icon': 'battery_unknown'
    }, {
        'type': 2,
        'name': 'Panel Voltage',
        'full_question': 'With the device disconnected, measure the panel voltage with a multimeter',
        'icon': 'border_all'
    }, {
        'type': 2,
        'name': 'Time of Measure',
        'full_question': 'Time of those measurement and weather at the time of measure. ',
        'icon': 'watch_later'
    }, {
        'type': 7,
        'name': 'System Issue Details Solutions',
        'full_question': 'What are the next steps to solve the issue (planned or already done)?',
        'icon': 'description',
        'min_answers': 1
    }]
}, {
    'name': 'Accessory Issue',
    'icon': 'error',
    'for_clients': False,
    'for_leads': False,
    'questions': [{
        'type': 4,
        'name': 'Accessory affected',
        'full_question': 'Accessory affected',
        'icon': '',
        'min_answers': 1,
        'choices': [{
            'order': 1,
            'value': 'Phone charging cable'
        }, {
            'order': 2,
            'value': 'Radio',
        }, {
            'order': 3,
            'value': 'TV',
        }, {
            'order': 4,
            'value': 'Satellite Receiver',
        }, {
            'order': 5,
            'value': 'Hairclipper',
        }, {
            'order': 6,
            'value': 'USB Splitter',
        }, {
            'order': 7,
            'value': 'Universal Charger',
        }, {
            'order': 7,
            'value': 'Other',
        }]
    }, {
        'type': 7,
        'name': 'Accessory issue description',
        'full_question': 'Accessory issue description',
        'icon': '',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Accessory issue solutions',
        'full_question': 'What are the next steps to solve the issue (planned or already done)?',
        'icon': '',
        'min_answers': 1
    }]
}, {
    'name': 'Battery Issue',
    'icon': 'error',
    'for_clients': False,
    'for_leads': False,
    'questions': [{
        'type': 1,
        'name': 'Sign of Tampering',
        'full_question': 'Is there sign of battery tampering?',
        'icon': 'pan_tool',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Tampering Check',
        'full_question': 'How did you check the tampering? Are the terminals painted?',
        'icon': 'pan_tool',
        'min_answers': 1
    }, {
        'type': 1,
        'name': 'Panel Disconnected',
        'full_question': 'Did the customer unplug the panel pin from the device?',
        'icon': 'content_cut',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Battery issue description',
        'full_question': 'Battery issue description',
        'icon': '',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Battery issue solutions',
        'full_question': 'What are the next steps to solve the issue (planned or already done)?',
        'icon': 'description',
        'min_answers': 1
    }, {
        'type': 0,
        'name': 'battery_group',
        'full_question': 'Battery',
        'icon': '',
        'max_answers': 1,
        'min_answers': 0,
        'sub_questions': [{
            'type': 2,
            'name': 'Battery Swap 1',
            'full_question': 'If a battery was swapped, please fill the new battery serial number',
            'icon': 'battery_alert'
        }, {
            'type': 2,
            'name': 'Battery Swap 2',
            'full_question': 'Battery #2 serial number (if any)',
            'icon': 'battery_alert'
        }, {
            'type': 2,
            'name': 'Battery Swap 3',
            'full_question': 'Battery #3 serial number (if any)',
            'icon': 'battery_alert'
        }]
    }]
}, {
    'name': 'Solar Panel Issue',
    'icon': 'error',
    'for_clients': False,
    'for_leads': False,
    'questions': [{
        'type': 1,
        'name': 'Panel Physical Damage',
        'full_question': 'Is there visible physical damage to the panel?',
        'icon': '',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Panel issue description',
        'full_question': 'Panel issue description',
        'icon': '',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Panel issue solutions',
        'full_question': 'What are the next steps to solve the issue (planned or already done)?',
        'icon': '',
        'min_answers': 1
    }]
}, {
    'name': 'Wiring Issue',
    'icon': 'error',
    'for_clients': False,
    'for_leads': False,
    'questions': [{
        'type': 4,
        'name': 'Wiring affectedWiring affected',
        'full_question': 'What part of the wiring was affected?',
        'icon': '',
        'choices': [{
            'order': 1,
            'value': 'Solar Panel Wiring (inside)'
        }, {
            'order': 2,
            'value': 'Solar Panel Wiring (outside)',
        }, {
            'order': 3,
            'value': 'Lamp Wiring (inside)',
        }, {
            'order': 4,
            'value': 'Lamp Wiring (outside)',
        }, {
            'order': 5,
            'value': 'Accessory Wiring',
        }, {
            'order': 6,
            'value': 'Other',
        }]
    }, {
        'type': 7,
        'name': 'Wiring issue description',
        'full_question': 'Wiring issue description',
        'icon': '',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Wiring issue solutions',
        'full_question': 'What are the next steps to solve the issue (planned or already done)?',
        'icon': '',
        'min_answers': 1
    }]
}, {
    'name': 'Other Issue',
    'icon': 'error',
    'for_clients': False,
    'for_leads': False,
    'questions': [{
        'type': 7,
        'name': 'Other Issue Description',
        'full_question': 'What is the issue in one sentence?',
        'icon': 'assignment_late',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Other Issue Additional Details',
        'full_question': 'More details about the problem.',
        'icon': 'description',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Other Issue Solutions',
        'full_question': 'What are the next steps to solve the issue (planned or already done)?',
        'icon': 'list',
        'min_answers': 1
    }]
}, {
    'name': 'Other device issue',
    'icon': 'error',
    'for_clients': False,
    'for_leads': False,
    'questions': [{
        'type': 4,
        'name': 'Other Device Issue symptom',
        'full_question': 'What is the issue with the Device?',
        'icon': '',
        'min_answers': 1,
        'choices': [{
            'order': 1,
            'value': 'USB ports malfunction'
        }, {
            'order': 2,
            'value': '12V output malfunction',
        }, {
            'order': 3,
            'value': 'User interface stuck',
        }, {
            'order': 4,
            'value': 'Not turning on',
        }, {
            'order': 5,
            'value': 'Other',
        }]
    }, {
        'type': 3,
        'name': 'Device Serial Number',
        'full_question': 'Device Serial Number',
        'icon': '',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Other Device Issue description',
        'full_question': 'Other Device Issue description',
        'icon': '',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Other Device Issue solutions',
        'full_question': 'What are the next steps to solve the issue (planned or already done)?',
        'icon': '',
        'min_answers': 1
    }]
}, {
    'name': 'Payment Issue',
    'icon': 'error',
    'for_clients': False,
    'for_leads': False,
    'questions': [{
        'type': 4,
        'name': 'Payment Issue Symptoms',
        'full_question': 'What are the symptoms?',
        'icon': '',
        'min_answers': 1,
        'choices': [{
            'order': 1,
            'value': 'Paid but no additional time was given'
        }, {
            'order': 2,
            'value': 'Paid but did not get the time expected',
        }, {
            'order': 3,
            'value': 'Could not send payment',
        }, {
            'order': 4,
            'value': 'Other',
        }]
    }, {
        'type': 7,
        'name': 'Payment issue description',
        'full_question': 'Payment issue description',
        'icon': '',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Payment issue solutions',
        'full_question': 'What are the next steps to solve the issue (planned or already done)?',
        'icon': '',
        'min_answers': 1
    }]
}, {
    'name': 'Activation Issue',
    'icon': 'error',
    'for_clients': False,
    'for_leads': False,
    'questions': [{
        'type': 4,
        'name': 'Activation Issue Symptoms',
        'full_question': 'What are the symptoms?',
        'icon': '',
        'min_answers': 1,
        'choices': [{
            'order': 1,
            'value': 'Sent an activation code but did not get an answer'
        }, {
            'order': 2,
            'value': 'Request code is always invalid',
        }, {
            'order': 3,
            'value': 'The device appears as "not registered"',
        }, {
            'order': 4,
            'value': 'Activation code received is invalid',
        }, {
            'order': 5,
            'value': 'Other',
        }]
    }, {
        'type': 7,
        'name': 'Activation issue description',
        'full_question': 'Activation issue description',
        'icon': '',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Activation issue solutions',
        'full_question': 'What are the next steps to solve the issue (planned or already done)?',
        'icon': '',
        'min_answers': 1
    }]
}, {
    'name': 'Device charging issue',
    'icon': 'error',
    'for_clients': False,
    'for_leads': False,
    'questions': [{
        'type': 7,
        'name': 'Device charging issue identification',
        'full_question': 'How did you determine that the problem was an issue with the device charging?',
        'icon': '',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Device charging issue description',
        'full_question': 'Device charging issue description',
        'icon': '',
        'min_answers': 1
    }, {
        'type': 3,
        'name': 'Device Serial Number',
        'full_question': 'Device Serial Number',
        'icon': '',
        'min_answers': 1
    }, {
        'type': 7,
        'name': 'Device charging issue solutions',
        'full_question': 'What are the next steps to solve the issue (planned or already done)?',
        'icon': '',
        'min_answers': 1
    }]
}, {
    'name': 'Referee Info',
    'scopes': {"client_and_lead": "optional"},
    'icon': 'location_city',
    'for_interactions': False,
    'questions': [{
        'type': 0,
        'name': 'activity_group',
        'full_question': 'Activities',
        'icon': '',
        'max_answers': 10,
        'min_answers': 0,
        'sub_questions': [{
            'type': 2,
            'name': 'referee_number',
            'full_question': 'Referee Phone Number',
            'icon': 'phone'
        }, {
            'type': 2,
            'name': 'referee_name',
            'full_question': 'Referee Full Name',
            'icon': 'perm_identity'
        }, {
            'type': 2,
            'name': 'referee_comment',
            'full_question': 'Comment from the referee about the Lead',
            'icon': 'question_answer'
        }, {
            'type': 4,
            'name': 'referee_type',
            'full_question': 'Choose the type of the Referee',
            'icon': 'assignment',
            'choices': [{
                'order': 1,
                'value': 'Village chief'
            }, {
                'order': 2,
                'value': 'Neighbour'
            }, {
                'order': 3,
                'value': 'Police officer'
            }, {
                'order': 4,
                'value': 'Family member'
            }, {
                'order': 5,
                'value': 'Friend'
            }, {
                'order': 6,
                'value': 'Other'
            }]
        }]
    }]
}, {
    'name': 'Mobile Money Info',
    'icon': 'credit_card',
    'for_interactions': False,
    'questions': [{
        'type': 8,
        'name': 'has_mpesa',
        'full_question': 'The prospect has a Mobile Money account',
        'icon': '',
    }, {
        'type': 2,
        'name': 'additional_info',
        'full_question': 'Additional Information About the Lead',
        'icon': 'edit',
    }]
}, {
    'name': 'House Structure Info',
    'icon': 'home',
    'for_interactions': False,
    'questions': [{
        'type': 2,
        'name': 'land_right',
        'full_question': 'Do you have a land right certificate issued by the government',
        'icon': 'home',
        'min_answers': 1
    }, {
        'type': 2,
        'name': 'ownership_certificate',
        'full_question': 'Do they have an ownership certificate for their house',
        'icon': 'home',
        'min_answers': 1
    }, {
        'type': 4,
        'name': 'material_roof',
        'full_question': 'Material of roof?',
        'icon': 'label',
        'min_answers': 1,
        'choices': [{
            'order': 1,
            'value': 'Not specified'
        }, {
            'order': 2,
            'value': 'Metal roof',
        }, {
            'order': 3,
            'value': 'Straw roof',
        }]
    }, {
        'type': 4,
        'name': 'material_walls',
        'full_question': 'Material of walls?',
        'icon': 'label',
        'min_answers': 1,
        'choices': [{
            'order': 1,
            'value': 'Not specified'
        }, {
            'order': 2,
            'value': 'Cement walls',
        }, {
            'order': 3,
            'value': 'Dirt walls',
        }]
    }, {
        'type': 4,
        'name': 'material_windows',
        'full_question': 'Materials for windows',
        'icon': 'label',
        'min_answers': 1,
        'choices': [{
            'order': 1,
            'value': 'Not specified'
        }, {
            'order': 2,
            'value': 'Glass',
        }, {
            'order': 3,
            'value': 'Plastic',
        }, {
            'order': 4,
            'value': 'Nothing',
        }, {
            'order': 5,
            'value': 'No windows',
        }]
    }, {
        'type': 3,
        'name': 'house_size',
        'full_question': 'Size(square meters)',
        'icon': 'home',
        'isInt': True,
        'min_answers': 1
    }, {
        'type': 3,
        'name': 'rooms',
        'full_question': 'Number of rooms',
        'icon': 'home',
        'isInt': True,
        'min_answers': 1
    }, {
        'type': 3,
        'name': 'houses',
        'full_question': 'Number of houses',
        'icon': 'home',
        'isInt': True,
        'min_answers': 1
    }, {
        'type': 3,
        'name': 'habitable_houses',
        'full_question': 'Number of habitable houses',
        'icon': 'home',
        'isInt': True,
        'min_answers': 1
    }]
}, {
    'name': 'Financial Info',
    'scopes': {"client_and_lead": "optional"},
    'icon': 'account_balance_wallet',
    'for_interactions': False,
    'questions': [{
        'type': 0,
        'name': 'activity_group',
        'full_question': 'Activities',
        'icon': '',
        'max_answers': 10,
        'min_answers': 0,
        'sub_questions': [{
            'type': 4,
            'name': 'activity_type',
            'full_question': 'Choose Activity Type',
            'icon': 'shop',
            'choices': [{
                'order': 1,
                'value': 'Agricultural Sector'
            }, {
                'order': 2,
                'value': 'Fishing sector',
            }, {
                'order': 3,
                'value': 'Industrial sector',
            }, {
                'order': 4,
                'value': 'Education Sector',
            }, {
                'order': 5,
                'value': 'Transportation sector',
            }, {
                'order': 6,
                'value': 'Service sector',
            }, {
                'order': 7,
                'value': 'Mining Sector',
            }, {
                'order': 8,
                'value': 'Other',
            }, {
                'order': 9,
                'value': 'Not specified',
            }]
        }, {
            'type': 2,
            'name': 'activity_name',
            'full_question': 'Activity Name',
            'icon': ''
        }, {
            'type': 3,
            'name': 'activity_income',
            'full_question': 'Activity Income',
            'icon': ''
        }, {
            'type': 4,
            'name': 'activity_income_frequency',
            'full_question': 'Choose income frequency',
            'icon': '',
            'choices': [{
                'order': 1,
                'value': 'Daily'
            }, {
                'order': 2,
                'value': 'Weekly',
            }, {
                'order': 3,
                'value': 'Monthly',
            }]
        }]
    }]
}, {
    'name': 'Crops Info',
    'icon': 'local_florist',
    'for_interactions': False,
    'questions': [{
        'type': 0,
        'name': 'crop_group',
        'full_question': 'Crops',
        'icon': '',
        'max_answers': 10,
        'min_answers': 1,
        'sub_questions': [{
            'type': 2,
            'name': 'crop_name',
            'full_question': 'Crop',
            'icon': ''
        }, {
            'type': 3,
            'name': 'crop_size',
            'full_question': 'Size (ha) ',
            'icon': ''
        }]
    }]
}, {
    'name': 'Livestock Info',
    'icon': 'info_outline',
    'for_interactions': False,
    'questions': [{
        'type': 0,
        'name': 'livestock_group',
        'full_question': 'What kind of livestock do you have?',
        'icon': '',
        'max_answers': 10,
        'min_answers': 1,
        'sub_questions': [{
            'type': 2,
            'name': 'livestock_name',
            'full_question': 'Livestock name',
            'icon': ''
        }, {
            'type': 3,
            'name': 'livestock_size',
            'full_question': 'Size (heads) ',
            'icon': ''
        }]
    }]
}, {
    'name': 'Business Info',
    'icon': 'business_center',
    'for_interactions': False,
    'questions': [{
        'type': 3,
        'name': 'distance',
        'full_question': 'Distance from Road/Center (meters)',
        'icon': 'location_city',
    }, {
        'type': 2,
        'name': 'intended_business',
        'full_question': 'Intended Business use of Solaris',
        'icon': 'business_center',
    }, {
        'type': 2,
        'name': 'seniority',
        'full_question': 'Overall seniority as business',
        'icon': 'account_balance_wallet',
        'min_answers': 1
    }, {
        'type': 0,
        'name': 'business_group',
        'full_question': 'Business',
        'icon': '',
        'max_answers': 10,
        'min_answers': 1,
        'sub_questions': [{
            'type': 4,
            'name': 'business_type',
            'full_question': 'Type of business',
            'icon': 'business_center',
            'min_answers': 1,
            'choices': [{
                'order': 1,
                'value': 'Motorbike Driver'
            }, {
                'order': 2,
                'value': 'Carpenter',
            }, {
                'order': 3,
                'value': 'Barbershop',
            }, {
                'order': 4,
                'value': 'Phone Charging',
            }, {
                'order': 5,
                'value': 'Stationary Shop',
            }, {
                'order': 6,
                'value': 'Grocery Shop',
            }, {
                'order': 6,
                'value': 'Other',
            }]
        }, {
            'type': 2,
            'name': 'business_detail',
            'full_question': 'Details of the business',
            'icon': 'business_center'
        }, {
            'type': 9,
            'name': 'start_date',
            'full_question': 'Time since the business started',
            'icon': 'business_center'
        }, {
            'type': 3,
            'name': 'turnover',
            'full_question': 'Turnover per week',
            'icon': 'attach_money'
        }, {
            'type': 8,
            'name': 'own_shop',
            'full_question': 'Do they own their own shop',
            'icon': 'shop'
        }, {
            'type': 8,
            'name': 'shop_outside',
            'full_question': 'Is the shop outside of their house',
            'icon': 'shop'
        }, {
            'type': 3,
            'name': 'number_clients',
            'full_question': 'Number of clients per week',
            'isInt': True,
            'icon': 'person'
        }, {
            'type': 8,
            'name': 'main_electricity',
            'full_question': 'Is the business based mainly on electricity use',
            'icon': 'flash_on'
        }]
    }]
}, {
    'name': 'Other External Loans',
    'icon': 'account_balance',
    'for_interactions': False,
    'questions': [{
        'type': 2,
        'name': 'borrow_reason',
        'full_question': 'Borrowing Reason',
        'icon': 'account_balance',
    }, {
        'type': 3,
        'name': 'borrow_amount',
        'full_question': 'Borrowed Amount',
        'icon': 'account_balance',
    }, {
        'type': 2,
        'name': 'borrow_lender',
        'full_question': 'Main Lender',
        'icon': 'account_balance',
    }, {
        'type': 3,
        'name': 'borrow_current',
        'full_question': 'Current Weekly Mortgage',
        'icon': 'account_balance',
    }]
}, {
    'name': 'Status',
    'icon': 'label',
    'for_interactions': False,
    'questions': [{
        'type': 4,
        'name': 'status',
        'full_question': 'Set Lead Status',
        'icon': 'label',
        'min_answers': 1,
        'choices': [{
            'order': 1,
            'value': 'Installed'
        }, {
            'order': 2,
            'value': 'Awaiting Delivery'
        }, {
            'order': 3,
            'value': 'Awaiting Payment'
        }, {
            'order': 4,
            'value': 'Promised to pay soon'
        }, {
            'order': 5,
            'value': 'To be reminded'
        }, {
            'order': 6,
            'value': 'Just asked to pay'
        }, {
            'order': 7,
            'value': 'Awaiting Decision'
        }, {
            'order': 8,
            'value': 'Awaiting Loan Approval'
        }, {
            'order': 9,
            'value': 'Awaiting Information'
        }, {
            'order': 10,
            'value': 'Loan Denied - Offer too expensive'
        }, {
            'order': 11,
            'value': 'Loan Denied - Awaiting Information'
        }, {
            'order': 12,
            'value': 'Ready to Buy - Awaiting Information'
        }, {
            'order': 13,
            'value': 'Nearly ready to Buy'
        }, {
            'order': 14,
            'value': 'Very Interested'
        }, {
            'order': 15,
            'value': 'Hesitating'
        }, {
            'order': 16,
            'value': 'Slightly Interested'
        }, {
            'order': 17,
            'value': 'Unknown'
        }, {
            'order': 18,
            'value': 'No longer interested'
        }, {
            'order': 19,
            'value': 'Loan Denied - Insufficient Income'
        }, {
            'order': 20,
            'value': 'Loan Denied - Too Far'
        }, {
            'order': 21,
            'value': 'Loan Denied - Other Reason'
        }, {
            'order': 22,
            'value': 'Discarded'
        }, {
            'order': 23,
            'value': 'Interested - Short-term'
        }, {
            'order': 24,
            'value': 'Interested - Long-term'
        }]
    }, {
        'type': 4,
        'name': 'reason',
        'full_question': 'Reason for not buying yet',
        'icon': 'label',
        'choices': [{
            'order': 1,
            'value': 'Need to speak to family'
        }, {
            'order': 2,
            'value': 'Waiting for harvest'
        }, {
            'order': 3,
            'value': 'Waiting for other income'
        }, {
            'order': 4,
            'value': 'Not sure about the value of the product'
        }, {
            'order': 5,
            'value': 'Not sure about the value of the aftersales'
        }, {
            'order': 6,
            'value': 'Do not have enough trust in the warranty'
        }, {
            'order': 7,
            'value': 'Need to think about it'
        }, {
            'order': 8,
            'value': 'Thinking about a competitor'
        }, {
            'order': 9,
            'value': 'Too expensive for them'
        }, {
            'order': 10,
            'value': 'The engagement fee or downpayment is too high for them'
        }, {
            'order': 11,
            'value': 'The waiting time for installation is too long'
        }, {
            'order': 12,
            'value': 'Ready to buy'
        }]
    }, {
        'type': 2,
        'name': 'comment',
        'full_question': 'Comment on status decision',
        'icon': 'comment',
    }, {
        'type': 9,
        'name': 'statusDate',
        'full_question': 'Status Change on:',
        'min_answers': 1,
        'icon': '',
    }, {
        'type': 9,
        'name': 'nextContactDate',
        'full_question': 'Next contact on:',
        'min_answers': 1,
        'icon': '',
    }]
}, {
    'name': 'Energy Use',
    'scopes': {"client_and_lead": "optional"},
    'for_interactions': False,
    'icon': 'lightbulb_outline',
    'questions': [{
        'type': 2,
        'name': 'lighting_tech',
        'full_question': 'Main lighting technology',
        'icon': 'lightbulb_outline',
    }, {
        'type': 3,
        'name': 'lighting_spending',
        'full_question': 'Lighting spending per week',
        'icon': 'lightbulb_outline',
    }, {
        'type': 3,
        'name': 'lighting_time',
        'full_question': 'Time spent acquiring lighting per week (hours)',
        'icon': 'lightbulb_outline',
    }, {
        'type': 3,
        'name': 'kerosene_litres',
        'full_question': 'Kerosene use per week (litres)',
        'icon': 'lightbulb_outline',
    }, {
        'type': 2,
        'name': 'cooking_tech',
        'full_question': 'Main cooking technology',
        'icon': 'local_dining',
    }, {
        'type': 3,
        'name': 'cooking_spending',
        'full_question': 'Cooking tech spending per week',
        'icon': 'local_dining',
    }, {
        'type': 3,
        'name': 'cooking_time',
        'full_question': 'Time spent acquiring cooking tech per week (hours)',
        'icon': 'local_dining',
    }, {
        'type': 2,
        'name': 'charging_tech',
        'full_question': 'Main phone charging technology',
        'icon': 'stay_current_portrait',
    }, {
        'type': 3,
        'name': 'charging_spending',
        'full_question': 'Phone charging spending per week',
        'icon': 'stay_current_portrait',
    }, {
        'type': 3,
        'name': 'charging_time',
        'full_question': 'Time spent charging phones per week (hours)',
        'icon': 'stay_current_portrait',
    }, {
        'type': 3,
        'name': 'hours_light',
        'full_question': 'Hours of lightning until sunset at home',
        'icon': 'lightbulb_outline',
    }, {
        'type': 3,
        'name': 'hours_study',
        'full_question': 'Hours of study after sunset for the children',
        'icon': 'school',
    }, {
        'type': 3,
        'name': 'child_grades',
        'full_question': 'Average grades of the children at school (if kids)',
        'icon': 'school',
    }]
}]


BILLING_TIERS = [30, 80, 200, 300, 1000, 2000, 5000, 10000] # Maximum amount of each tier, in USD
NUMBER_OF_BILLING_TIERS = len(BILLING_TIERS)+1 # The last tier is for the items above Tier[-1]

# Ordered billing feature keys used in the PaygOps Features card (billing page)
# This defines ONLY the order and stable keys; labels and toggle mapping are defined in the admin layer.
BILLING_ORDERED_FEATURE_KEYS = [
    "Leads",
    "OneOffPayments",
    "CreditAndSubscriptionPayments",
    "Ticketing",
    "Inventory",
    "Analytics",
    "OfflineAgentApp",
    "ClientGroup",
    "SSO",
    "MobileSSO",
    "AuditLogs",
    "OffTaking",
    "PaymentIntegrationAndRouting",
    "APIAccess",
    "PaygoDevices",
    "TaskSystem",
    "AutomatedMessagesAndSms",
]

LAST_UPDATED_DEFINITION = 'The date at which the record was last updated in the Analytical DB (for internal use of PaygOps)'

PERSONAL_INFO_CONFIG = ['first_name', 'surname', 'birthdate', 'gender', 'phone_number', 'gps_coordinates', 'preferred_sms_language', 'verbal_language', 'profile_picture', 'get_gps_from_picture', 'home_use', 'business_use','status','reasons_for_not_buying', 'comment_on_status', 'next_planned_contact','portfolio','client_group',]
USER_JOURNEY_INFO_CONFIG =['first_name', 'surname', 'birthdate', 'gender', 'phone_number', 'gps_coordinates', 'preferred_sms_language', 'verbal_language', 'profile_picture','portfolio','client_group', 'home_use', 'business_use', 'status', 'lead_generator', 'l0_entity_id', 'custom_id']

VIEW_STOCK_PERMS = ['InStockViewStock', 'WithUsersViewStock', 'WithMeViewStock',
              'WithClientsViewStock']
VIEW_GLOBAL_STOCK_PERMS = ['OrphanedViewStock']
CREATE_STOCK_MOVE_PERMS = ['FromOrphanedMoveStock', 'FromInStockMoveStock',
                'FromUsersMoveStock', 'FromWithMeMoveStock', 'ToOrphanedMoveStock',
                'ToInStockMoveStock', 'ToUsersMoveStock', 'ToWithMeMoveStock']


MAX_CREDIT_PER_REPAYMENT_ALLOWED = 24*365*100 # 100 years

CUSTOM_BUTTON_TARGET_PAGES = {
    "client": "Client Page",
    "lead": "Lead Page",
    "contract": "Contract Page",
}

CUSTOM_BUTTON_TYPE = {
    'action': 'Action',
    'view': 'View',
}
CUSTOM_BUTTON_VARIABLES_INFO = [
    'client_id', 'name', 'custom_id', 'client_phone_number', 'user_id', 'user_name', 'contract_id', 'contract_reference', 'contract_serial_number', 'contract_phone_number', 'client_custom_id', 'lead_id', 'lead_name', 'lead_phone_number',
]

CUSTOM_BUTTON_VARIABLES_BY_PAGE = {
    "client": [
        ("client_id", "Client ID"),
        ("name", "Client Name"),
        ("custom_id", "Custom ID"),
        ("client_phone_number", "Client Phone Number"),
        ("user_id", "User ID"),
        ("user_name", "User Name"),
    ],
    "contract": [
        ("client_id", "Client ID"),
        ("name", "Client Name"),
        ("custom_id", "Custom ID"),
        ("client_phone_number", "Client Phone Number"),
        ("contract_reference", "Contract Reference"),
        ("contract_serial_number", "Contract Serial Number"),
        ("user_id", "User ID"),
        ("user_name", "User Name"),
    ],
    "lead": [
        ("lead_id", "Lead ID"),
        ("lead_name", "Lead Name"),
        ("custom_id", "Custom ID"),
        ("lead_phone_number", "Lead Phone Number"),
        ("user_id", "User ID"),
        ("user_name", "User Name"),
    ],
}
CUSTOM_LINKED_OBJECT_TYPE = {
    'client':'client', 
    'lead':'lead', 
    'device':'device', 
    'contract':'contract'
}
CUSTOM_TASK_ACTION_TYPE = {
    'object': 'Go To Object',
    'interaction': 'Create Interaction',
    'user_journey': 'User Journey',
    'no_action': 'No Action'
}

COLOR_OPTIONS = [
    'gray', 'black', 'blue', 'teal', 'green', 'amber', 'yellow', 'red', 'pink', 'purple'
]

FEATURE_NAME_MAP = {
    'SalesFeatures': 'Sales (Leads)',
    'LumpSumContracts': 'Lump-Sum Contracts (One-Off Payments)',
    'LoanAndSubscriptionContracts': 'Loan and Subscription Contracts (Credits & Subscription Payments)',
    'AfterSales': 'After Sales (Ticketing)',
    'Inventory': 'Inventory',
    'ClientGroups': 'Client Groups',
    'AddOnsConfiguration': 'Add-ons',
    'AuditLogs': 'Audit Logs',
    'PaymentManagement': 'Payment Management (Autopayments)',
    'AutomatedMessagesSMS': 'Automated Messages and SMS',
    'ApiAccess': 'API Access',
    'BulkActions': 'Bulk Actions',
    'PaygoDevices': 'PAYGO',
    'OffTaking': 'Offtaking',
}

FEATURE_FLAGS_CONFIG = {
    'SalesFeatures':[
        'ViewCreatedLeads', 'ViewLeadGenerators', 'EditLeads','ViewOwnLeadGenerators',
        'ViewBadgeLeads', 'ViewLeads', 'AddForms', 'EditForms', 'AddLeadGenerators',
        'EditLeadGenerators', 'ConfigureSalesManagementAdmin', 'ViewDashboards',
        'ConfigurePersonalInfoAdmin'
    ],
    'LumpSumContracts':[
        'ViewLeads', 'ViewClients', 'ViewAddonOffers', 'AddAddonOffers', 'EditAddonOffers',
        'AddLeads', 'EditLeads', 'EditClients','ViewPayments', 'ViewOrphanedPayments', 'AddPayments',
        'AdjustBalanceAndReconcilePayments', 'EditWalletPayments', 'ViewReversedPayments','AddReversedPayments',
        'HandleReversedPayments', 'ViewDashboards'
    ],
    'LoanAndSubscriptionContracts':[
        'ViewLoanOffers', 'AddLoanOffers', 'EditLoanOffers', 'ViewLeads', 'AddLeads',
        'EditLeads', 'ViewAddonOffers', 'AddAddonOffers', 'EditAddonOffers', 'ViewClients',
        'EditClients', 'ViewPayments', 'ViewOrphanedPayments', 'AddPayments', 'AdjustBalanceAndReconcilePayments',
        'EditWalletPayments', 'ViewReversedPayments', 'AddReversedPayments', 'HandleReversedPayments',
        'ViewDashboards'
    ],
    'AfterSales':[
        'ViewInteractions', 'EditInteractions','AddInteractions', 'ViewIssues', 'EditIssues',
        'AddIssues', 'ViewPlanning', 'EditPlanning', 'AddPlanning', 'ViewLeads', 'AddLeads',
        'EditLeads', 'EditInteractionsSettingsForms', 'AddForms', 'ViewForms', 'EditForms',
        'ViewDashboards', 'DeletePlanning', 'DeleteInteractions', 'DeleteNotesIssues'
    ],
    'Inventory':[
        'InStockViewStock', 'WithUsersViewStock', 'WithMeViewStock', 'WithClientsViewStock',
        'OrphanedViewStock', 'FromOrphanedMoveStock', 'FromInStockMoveStock', 'FromUsersMoveStock',
        'FromWithMeMoveStock', 'ToOrphanedMoveStock', 'ToInStockMoveStock', 'ToUsersMoveStock',
        'ToWithMeMoveStock', 'ManageQuantityViewStock'
    ],
    'ClientGroups':['AddClientGroups', 'EditClientGroups'],
    'AddOnsConfiguration':['ViewAddonOffers', 'AddAddonOffers', 'EditAddonOffers'],
    'AuditLogs':['ViewActivityLogAdmin'],
    'PaymentManagement':['ConfigurePaymentRouterAdmin', 'ConfigurePaymentManagementAdmin'],
    'AutomatedMessagesSMS':['ConfigureAutomatedMessagesAdmin', 'ViewMessages', 'EditCustomSMSAdmin'],
    'OffTaking':['AddPurchasingAddOns'],
    'ApiAccess':['AddAPIHook', 'DeleteAPIHook', 'CreateAPITokenAdmin', 'ViewAPIDocumentation'],
    'BulkActions':['APICallerAdmin'],
    'PaygoDevices':['ViewPaygoDevices']
}


SMS_STATUS_MAP = {
    "created": "Created on PaygOps, not yet sent to the gateway (linking PaygOps and the service provider)",
    "processed": "Sucessfully sent to the gateway (linking PaygOps and the service provider)",
    "sent": "The service provider has accepted the message",
    "sending_failure": "The service provider is unreachable or returning errors",
    "sending_rejected": "The service provider rejected the message but did not provide a reason. Get in touch with them for more information. ",
    "sending_rejected_config": "The service provider rejected the message due to invalid configuration (invalid sender ID or no balance, or other issue with account such as being blocked)",
    "sending_rejected_msisdn": "The service provider rejected the message due to invalid phone number",
    "sending_rejected_flagged": "The service provider rejected the message due to an anti-spam system or similar",
    "delivered_telco": "The message was delivered to the client's mobile network operator",
    "delivered_final": "The message was delivered to the client's phone",
    "delivery_failure": "The message was sent but could not be delivered but the service provider did not provide a reason. Get in touch with them for more information. ",
    "delivery_rejected": "The message was sent but could not be delivered because the client's mobile network operator rejected it (it can be due to invalid phone number, anti-spam system or other reasons)",
    "delivery_failure_absent": "The message could not be delivered because the client's phone was off or not reachable for too long",
    "delivery_rejected_msisdn": "The message could not be delivered because the client's phone number is invalid or deactivated",
    "delivery_rejected_flagged": "The message could not be delivered because the message was flagged as SPAM by the mobile network operator or the client has a setting to reject any commercial messages"
}

SMS_STATUS_MAP_SHORT = {
    "created": "Created on PaygOps",
    "processed": "Sent to Gateway",
    "sent": "Sent to Provider",
    "sending_failure": "Could not send to provider",
    "sending_rejected": "Rejected by provider (generic)",
    "sending_rejected_config": "Rejected by provider (config)",
    "sending_rejected_msisdn": "Rejected by provider (phone number)",
    "sending_rejected_flagged": "Rejected by provider (SPAM)",
    "delivered_telco": "Delivered to Telco",
    "delivered_final": "Delivered to Client",
    "delivery_failure": "Delivery Failure (generic)",
    "delivery_rejected": "Delivery Failure (rejected)",
    "delivery_failure_absent": "Delivery Failure (absent)",
    "delivery_rejected_msisdn": "Delivery Failure (phone number)",
    "delivery_rejected_flagged": "Delivery Failure (spam)"
}

MESSAGE_RECEIVERS = {
    "send_message_phone_receiver": "Pick Receiver",
    "send_message_client": "Client",
    "send_message_lead": "Lead",
    "send_message_user": "User"
}
SENDER_USER_TYPES = {
    "automation": "Automation",
    "manually_sent": "Manually Sent"
}


B2C_PAYMENT_STATUS_MAP = {
    'successful': {'text': 'Success', 'color': 'green'},
    'pending': {'text': 'Pending', 'color': 'amber'},
    'pending_confirmation': {'text': 'Pending Confirmation', 'color': 'amber'},
    'cancelled': {'text': 'Cancelled', 'color': 'gray'},
    'insufficient_funds': {'text': 'Insufficient Fund', 'color': 'red'},
    'invalid_user_account': {'text': 'Invalid User Account', 'color': 'red'},
    'generic_failure': {'text': 'Generic Failure', 'color': 'red'},
    'timeout_failure': {'text': 'Timeout failure', 'color': 'red'},
    'gateway_failure': {'text': 'Gateway Failure', 'color': 'red'},
}

B2C_FAILED_STATUSES = ['cancelled', 'insufficient_funds', 'invalid_user_account', 'generic_failure', 'timeout_failure', 'gateway_failure']