import os
from constants import *
import json

# ----- Environment type config ----

ENV_VAR = os.getenv("ENV_VAR", 'PROD')
BUILD_MODE = os.getenv("BUILD_MODE", '0')
AUTOMATED_TESTING = os.getenv("AUTOMATED_TESTING", '0') in ['1', 1]
MIGRATE_MODE = os.getenv('MIGRATE_MODE', False)
DISABLE_ANALYTICAL_DB = os.getenv('DISABLE_ANALYTICAL_DB', False)
DISABLE_HEAVY_TASKS = os.getenv('DISABLE_HEAVY_TASKS', False)
TRIGGER_WEBHOOK_AFTER_EDIT = os.getenv('TRIGGER_WEBHOOK_AFTER_EDIT', False)
SPLIT_SERVER_MODE = os.getenv('SPLIT_SERVER_MODE', 'STANDARD') # STANDARD: No split, MAIN: Main split server (data), SECONDARY: Secondary split server (process)
IS_SECONDARY = (SPLIT_SERVER_MODE == 'SECONDARY')
ENABLE_ENTERPRISE_FEATURES = os.getenv('ENABLE_ENTERPRISE_FEATURES', '0') in ['1', 'true', 'True', True, 1]
IS_ENTERPRISE_EDITION = ENABLE_ENTERPRISE_FEATURES
EDITION = os.getenv('EDITION', 'oss' if not IS_ENTERPRISE_EDITION else 'enterprise')

try: FAILED_WEBHOOKS_THRESHOLD = int(os.getenv('FAILED_WEBHOOKS_THRESHOLD', ''))
except ValueError: FAILED_WEBHOOKS_THRESHOLD = 50

## Azure Config
WABS_ACCOUNT_NAME = os.getenv('WABS_ACCOUNT_NAME', '')
WALE_CONTAINER_NAME = os.getenv('WALE_WABS_PREFIX', '').replace('wabs://', '')
WABS_ACCESS_KEY = os.getenv('WABS_ACCESS_KEY', '')


# ----- Feature Flags ----



# user tracking
TRACKED_ENDPOINTS = [
    'overview',
    'client'
]
TRACK_ALL = True


# Accounting config
LastTransferIncluded = True
ExpenseReceiptCompulsory = False

# SMS Delivery config
gateway_delivery_enabled = True
delayed_gateway_post = False

# For payg loan system
auto_link_lead_account_to_client = False

# ---- Defaults ----

# This is the list of district, to be filled only if the client specifically asks for it
DistrictList=['Main district']


auto_send_payment_reminder_sms=True #to be replaced by SendPaymentReminderMessages
sms_reminders_days_before_expiry=[1] # to be replaced by PaymentRemindersDaysBeforeExpiry

# both to be replaced by TimeSendingPaymentReminder
sms_reminders_hour_of_day=10
sms_reminders_minute_of_day=30

web_language = 'EN' #to be replaced with DefaultWebLanguage

# to be replaced by FirstDayOfWeek
first_day_of_week = 0 # 0 is monday

CountryName = 'Spain'
CountryDescriptor = 'Spanish'
PhoneExtension = '234'
PhoneLength = 10 # The first number shall not be 0 (it should be the secondary extension, like 7, then all other number should be there
PhoneLengthMin = 10
target_timezone = 'UTC' #'Europe/Madrid'
MainCurrencySymbol = 'USD'

# Organization specific settings

default_language = 'EN' # to be replaced with DefaultSMSUsersLanguage
default_client_language = 'EN' # to be replaced with DefaultSMSClientsLanguage

# ----- Testing
IS_TESTING = False
if ENV_VAR == 'TEST':
    IS_TESTING = True
    TEST_MODE = True
    LogAccess = False
    LogLogin = False
    TEMP_PATH = tempfile.mkdtemp()
    NaN_VAL = None # Trick to support SQLite
else:
    TEST_MODE = False
    LogAccess = True
    LogLogin = True
    NaN_VAL = float('nan')


# ----- Environment ----

if ENV_VAR == 'TEST':
    CACHING_ENABLED = os.getenv('CACHING_ENABLED', None)
else:
    CACHING_ENABLED = os.getenv('CACHING_ENABLED', True)

MIGRATIONS_DIR = os.getenv('MIGRATION_DIR', os.path.join(CURRENT_DIR, 'shared/migrations/'))
GLOBAL_SCALE = int(os.getenv('GLOBAL_SCALE', 2))
FREQUENT_ADB_UPDATE = os.getenv('FREQUENT_ADB_UPDATE', 0) in ['1', 1]

# DB connections
REMOTE_ADB_ADDRESS = os.getenv('REMOTE_ADB_ADDRESS', None)
IS_ADB_SERVER = os.getenv('IS_ADB_SERVER', 0) not in [1, '1']
if IS_SECONDARY:
    REDIS_HOST = os.getenv('REDIS_SERVER_ADDRESS', os.getenv('MAIN_SERVER_IP'))
    REDIS_PORT = 37227
    PG_HOST = os.getenv('PG_HOST', os.getenv('MAIN_SERVER_IP', 'postgres'))
    PG_PORT = '37226'
    if IS_ADB_SERVER:
        ANALYTICAL_DB_HOST = os.getenv('ANALYTICAL_DB_HOST', os.getenv('MAIN_SERVER_IP'))
        ANALYTICAL_DB_PORT = '31441'
    else:
        ANALYTICAL_DB_HOST = os.getenv('ANALYTICAL_DB_HOST', 'analytical_db')
        ANALYTICAL_DB_PORT = '5432'
else:
    REDIS_HOST = os.getenv('REDIS_SERVER_ADDRESS', 'redis')
    REDIS_PORT = 6379
    PG_HOST = os.getenv('PG_HOST', 'postgres')
    PG_PORT = '5432'
    ANALYTICAL_DB_HOST = os.getenv('ANALYTICAL_DB_HOST', 'analytical_db')
    ANALYTICAL_DB_PORT = '31441' if ANALYTICAL_DB_HOST != 'analytical_db' else '5432'

REDIS_DBS = {
    'worker_app': '0',
    'redbeat': '1',
    'worker_green_app': '8'
}

BOUNCER_ENABLED = os.getenv('PGBOUNCER_ENABLED', '0') == '1'
if BOUNCER_ENABLED and IS_SECONDARY:
    MAIN_PG_HOST = 'pgbouncer'
    MAIN_PG_PORT = '5432'
else:
    MAIN_PG_HOST = PG_HOST
    MAIN_PG_PORT = PG_PORT

PG_USER = os.getenv('PG_USER', 'solaris_deploy')
PG_PASSWORD = os.getenv('PG_PASSWORD', '')
VERSION = os.getenv('VERSION', 'local')
COMMIT_SHA = os.getenv('COMMIT_SHA', 'local')
BRANCH = os.getenv("PAYG_BRANCH", "release")
HOOK_TIMEOUT = int(os.getenv('HOOK_TIMEOUT', '90'))

PAYG_API_URL_BASE = os.getenv('ALTERNATE_PAYG_URL', os.getenv('PAYG_URL', None))
if not PAYG_API_URL_BASE:
    PAYG_API_URL_BASE = 'localhost'

LOGIN_PAYG_URL = os.getenv('LOGIN_PAYG_URL', PAYG_API_URL_BASE)

default_payg_api_url = 'localhost:6789'
PAYG_API_URL = f'https://{PAYG_API_URL_BASE}'
if ENV_VAR == 'TEST':
    PAYG_API_URL = f'http://{default_payg_api_url}'
PAYG_API_URL = os.getenv('PAYG_API_URL', PAYG_API_URL)

if '.paygops.com' in PAYG_API_URL_BASE:
    INSTANCE_NAME = PAYG_API_URL_BASE.split('.paygops.com')[0]
else:
    INSTANCE_NAME = PAYG_API_URL_BASE

DEFAULT_PASSWORD_COMMUNICATION = os.getenv('DEFAULT_PASSWORD_COMMUNICATION', 'email')

secret_key = os.getenv('SECRET_KEY', '')
if ENV_VAR == 'TEST':
    # This default secret key is just for local testing, NEVER USE IT IF PUBLISHING TO A SERVER
    secret_key = 'ZXJtaXNzaW9ucyI6RldmljZXM6ZWRpdDeyJwWyJkZXZpY2VzOmxpc3QiLCJkZXZpY2VzOmdldCIsIm'
api_secret = secret_key

# Monitoring platform
monitoring_api_key = os.getenv("MONITORING_API_KEY", '')
monitoring_api_url = os.getenv("MONITORING_API_URL", '')
apm_username = os.getenv('APM_USERNAME', '')
apm_password = os.getenv('APM_PASSWORD', '')

# Login platform
LOGIN_PLATFORM_URL = os.getenv("LOGIN_OAUTH_URL", '')
LOGIN_JWT_SECRET = os.environ.get("LOGIN_JWT_SECRET", "")

# Doc360 SSO
DOC360_CALLBACK_URL = os.getenv('DOC360_CALLBACK_URL', '')
DOC360_SSO_CLIENT_ID = os.getenv('DOC360_SSO_CLIENT_ID', '')
DOC360_SSO_CLIENT_SECRET = os.getenv('DOC360_SSO_CLIENT_SECRET', '')

def safe2int(x, d):
    try:
        return int(str(x))
    except ValueError:
        return d

RUNTIME_WARNING_THRESHOLD = safe2int(os.getenv('RUNTIME_WARNING_THRESHOLD'), 120)
LONG_RUNNING_TASK_THRESHOLD = safe2int(os.getenv('LONG_RUNNING_TASK_THRESHOLD'), 720)
QUEUED_TASK_WARNING_THRESHOLD = safe2int(os.getenv('QUEUED_TASK_WARNING_THRESHOLD'), 25)

# ----- DEVICE CONFIG -----

# This function is just needed for migration and retro-compatibility of the config files
def get_device_api_name_from_url(url):
    if 'amped' in url:
        return 'AMP'
    if 'solaris' in url:
        return 'SOL'
    if 'victron' in url:
        return 'VIC'
    if 'biolite' in url:
        return 'BIO'
    if 'glp' in url:
        return 'GLP'
    else:
        return None

device_api_key = os.getenv("DEVICE_API_KEY", '')
device_api_url = os.getenv("DEVICE_API_URL", '')
device_api_type = os.getenv("DEVICE_API_TYPE", '')

if ENV_VAR == 'TEST':
    device_api_key = 'example'
    device_api_url = 'http://solaris:5555/v1/'
    device_api_type = 'TWO_WAY_CODE'

device_api_name = os.getenv("DEVICE_API_NAME", get_device_api_name_from_url(device_api_url))

default_all_devices_apis = {}
if device_api_name:
    default_all_devices_apis = {
        device_api_name: {
            'device_api_key': device_api_key,
            'device_api_url': device_api_url,
            'device_api_type': device_api_type,
            'device_api_full_name': '',
            'device_api_version': "v1",
            "device_api_code": device_api_name,
            "offline_mode": "DISABLED",
            "supports_monitoring_data": "DISABLED",
            "supported_offer_type": "TIME_BASED",
            "supported_units": {}
        }
    }
    
if ENV_VAR == 'TEST':
    default_all_devices_apis.update({
        "1WY": {
            'device_api_key': 'xxx',
            'device_api_url': 'https://xxx.test.com/v1/',
            'device_api_type': 'ONE_WAY_CODE',
            'device_api_full_name': '',
            'device_api_version': "v2",
            "device_api_code": "1WY",
            "offline_mode": "ENABLED",
            "supports_monitoring_data": "ENABLED",
            "supported_offer_type": "BOTH",
            "supported_units": {"KWH": "kWh"}
        }
    })

#replaced by AllDeviceAPIS
all_device_apis = json.loads(os.getenv('ALL_DEVICE_APIS', json.dumps(default_all_devices_apis)))

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')

# Helper function to check if AI features are enabled
def AI_ENABLED():
    """Returns True if AI features are enabled (ANTHROPIC_API_KEY is set and not empty)"""
    return bool(ANTHROPIC_API_KEY and ANTHROPIC_API_KEY.strip())

# Google Maps API Key
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', '')

# Google reCAPTCHA Site Key (public key used in frontend)
GOOGLE_CAPTCHA_SITE_KEY = os.getenv('GOOGLE_CAPTCHA_SITE_KEY', '')

# Email addresses
SUPPORT_EMAIL = os.getenv('SUPPORT_EMAIL', '')

# Support URL
SUPPORT_URL = os.getenv('SUPPORT_URL', '')

default_fallback_device_type = 'DISABLED'
default_hide_prefix_fallback_device_type = False
default_npg_device_enabled = True
default_gps_surface_measurement_unit = 'ha'
default_online_training_url = 'https://www.youtube.com/playlist?list=PLU7UyB0I4IahcmY_MYsi2W77JoQlfkeHP'

def is_user_journey_editor_enabled():
    from shared.services.settings_service import SettingsService
    return SettingsService.get_setting('FeatureToggles').get('user_journey_editor', False)


# ----- DEV CONFIG -----

reload_templates = os.getenv('RELOAD_TEMPLATES', 'false').lower() in ['true', '1', 'True', True]

def is_dev_mode():
    if ENV_VAR == 'TEST' or ENV_VAR == 'DEV' or reload_templates == True:
        return True
    else:
        return False

def is_test_platform():
    if is_dev_mode():
        return True
    for test_string in ['staging', 'demo', 'feature-test', 'localhost', 'translation']:
        if test_string in PAYG_API_URL:
            return True
    return False

IS_TEST_PLATFORM = False

if is_test_platform():
    IS_TEST_PLATFORM = True

# ----------- MODES -----------

INSTALL_MODE = False  # This will only be set true by the install script to avoid the mappings being generated

def is_production_server():
    if PAYG_API_URL_BASE and PAYG_API_URL_BASE != 'localhost' and '.ngrok.app' not in PAYG_API_URL_BASE:
        return True
    return False

latest_main_db_version_pg = 1
latest_accounting_db_version_pg = 1
latest_sms_db_version_pg = 1

#Mobile version: This should be updated manually everytime the mobile app version is updated
mobile_app_version = "2.23.1"

def check_if_custom_app(request):
    custom_app_cookie = request.cookies.get('custom_app')
    return custom_app_cookie == 'true' or request.headers.get('App') == 'custom' or 'PaygOps Custom App' in str(request.user_agent) # This means its a custom APK or offline mobile app
