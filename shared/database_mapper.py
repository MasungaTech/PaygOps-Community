import os
from datetime import datetime
import pytz
import config
from config import ENV_VAR
from accounting_system.accounting_db import accounting_db as adb
from core_system.core_entities import db as mdb
from shared.model.activity_log_db import audit_db
from messages_system.models.sms_db import sms_db
from pony import orm


class DatabaseMapper:
    @staticmethod
    def is_install_mode():
        INSTALL_MODE = os.getenv('INSTALL_MODE', False)
        return True if INSTALL_MODE in [True, 'true', 'True', '1'] else False

    @staticmethod
    def is_migrate_mode():
        MIGRATE_MODE = os.getenv('MIGRATE_MODE', False)
        return True if MIGRATE_MODE in [True, 'true', 'True', '1'] else False

    @staticmethod
    def is_test_mode():
        return ENV_VAR == 'TEST'

    @classmethod
    def generate_map(cls, include_analytical=False):
        try:
            if cls.is_install_mode():
                print('---- Generate Mapping - INSTALL ----')
                cls.generate_all(include_analytical=include_analytical, create_tables=True)
                return
            
            if cls.is_migrate_mode():
                print('---- Generate Mapping - MIGRATE ----')
                cls.generate_all(include_analytical=include_analytical, check_tables=False)
                return
            
            if cls.is_test_mode():
                print('---- Generate Mapping - MIGRATE ----')
                cls.generate_all(include_analytical=include_analytical, create_tables=True, check_tables=True)
                return
            
            print('---- Generate Mapping ----')
            cls.generate_all(include_analytical=include_analytical, check_tables=False)

            if include_analytical:
                cls._generate_new_analytical_if_needed()
                
        except orm.core.BindingError:
            print('Mapping already generated')
            
    @staticmethod
    def generate_all(include_analytical=False, **kwargs):
        if include_analytical:
            from data_system.analytical_db.analytical_db import analytical_db
            analytical_db.generate_mapping(create_tables=True)
        from shared.model.hook_model import Webhook
        if config.ENABLE_ENTERPRISE_FEATURES:
            from task_system.models.task import Task
            from task_system.models.task_category import TaskCategory
        mdb.generate_mapping(**kwargs)
        adb.generate_mapping(**kwargs)
        audit_db.generate_mapping(create_tables=True)
        sms_db.generate_mapping(create_tables=True)

    @classmethod
    def _generate_new_analytical_if_needed(cls):
        from data_system.analytical_db.analytical_db import Metadata
        with orm.db_session:
            meta = Metadata.get(table='CREATION_DATE')
            if not meta:
                meta = Metadata(table='CREATION_DATE', updated_on=datetime.now())
