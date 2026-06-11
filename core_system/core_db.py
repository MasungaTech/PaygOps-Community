from accounting_system.accounting_db import accounting_db as adb
from core_system.core_entities import db as mdb
from messages_system.models.sms_db import sms_db
from shared.cache.redis_config import *
import os
from config import ENV_VAR


def is_install_mode():
    INSTALL_MODE = os.getenv('INSTALL_MODE', False)
    return True if INSTALL_MODE in [True, 'true', 'True', '1'] else False

def is_migrate_mode():
    MIGRATE_MODE = os.getenv('MIGRATE_MODE', False)
    return True if MIGRATE_MODE in [True, 'true', 'True', '1'] else False

def is_test_mode():
    return ENV_VAR == 'TEST'


if is_install_mode():
    print('---- Generate Mapping - INSTALL ----')
    mdb.generate_mapping(create_tables=True)
    adb.generate_mapping(create_tables=True)
    sms_db.generate_mapping(create_tables=True)
elif is_migrate_mode():
    print('---- Generate Mapping - MIGRATE ----')
    mdb.generate_mapping(check_tables=False)
    adb.generate_mapping(check_tables=False)
    sms_db.generate_mapping(check_tables=False)
elif is_test_mode():
    mdb.generate_mapping()
    adb.generate_mapping()
    sms_db.generate_mapping()
else:
    print('---- Generate Mapping ----')
    mdb.generate_mapping(create_tables=True)
    adb.generate_mapping(create_tables=True)
    sms_db.generate_mapping(create_tables=True)
