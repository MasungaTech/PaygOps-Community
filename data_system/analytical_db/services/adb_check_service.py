from pony import orm
from datetime import datetime, timedelta
from data_system.analytical_db.services.model_update_service import ModelUpdateService
from data_system.analytical_db.services.update_service import AnalyticalDBUpdateService
from shared.logger.loggers import LogService
from shared.helpers.date_helper import timedelta_to_hours
from decimal import Decimal
import random


class ADBCheckService:

    ADB_UPDATE_WARNING_THRESHOLD = 6 # 6 hours
    SAMPLE_SIZE = 5000
    ISSUE_SAMPLE_SIZE = 10
    SENSITIVE_MODE = False

    @classmethod
    def warn_if_last_update_too_old(cls):
        models = AnalyticalDBUpdateService.MODELS
        warning_time = datetime.now() - timedelta(hours=cls.ADB_UPDATE_WARNING_THRESHOLD)
        models_not_updated = {}
        for model in models:
            latest_adb_update, latest_db_update = cls._get_latest_updates_for_model(model)
            if latest_adb_update < warning_time:
                if latest_db_update and latest_db_update > warning_time:
                    models_not_updated[model.__name__] = {
                        'latest_adb_update': str(latest_adb_update),
                        'latest_db_update': str(latest_db_update),
                        'update_delay_hours': str(round(timedelta_to_hours(latest_db_update - latest_adb_update), 2))
                    }
        if models_not_updated:
            LogService.Warning('Some models were not updated in time (see details)', other_data={'details': models_not_updated})
        else:
            LogService.Event('Analytical DB was updated as expected.')

    @classmethod
    def warn_if_updated_objects_have_mismatching_data(cls):
        models = AnalyticalDBUpdateService.MODELS
        for model in models:
            cls._check_model(model)

    @classmethod
    @orm.db_session
    def _check_model(cls, model):
        affected_ids = []
        issue_samples = {}
        updated_objects = cls._get_up_to_date_objects_in_adb(model)
        ids = list(orm.select(o.id for o in updated_objects)[:])
        sample_size = min(cls.SAMPLE_SIZE, len(ids))
        if sample_size == 0:
            return
        ids_to_check = random.sample(ids, sample_size)
        del ids
        batch_size = 100
        for batch_start in range(0, len(ids_to_check), batch_size):
            with orm.db_session():
                batch_ids = ids_to_check[batch_start:batch_start + batch_size]
                objects_to_check = orm.select(o for o in model.base_model if o.id in batch_ids).order_by(1)
                objects_to_check = model.selector(objects_to_check)[:]
                adb_objects = orm.select(o for o in model if o.id in batch_ids)[:] # Preload for cache
                LogService.Event(f'Checking batch {batch_start // batch_size + 1} ({len(batch_ids)}) {model.__name__} for coherence...')
                for obj in objects_to_check:
                    if model in AnalyticalDBUpdateService.REUPDATE:
                        original_object = model.converter(obj, reupdate=True)
                    else:
                        original_object = model.converter(obj)
                    obj_id = getattr(obj, 'id', None) or obj[0]
                    adb_object = model.get(id=obj_id).to_dict(with_lazy=True)
                    diff = cls._objects_have_differences(original_object, adb_object, model)
                    if diff:
                        affected_ids.append(obj_id)
                        # We only send diff data for a few objects to avoid having a log that is too big
                        if len(affected_ids) <= cls.ISSUE_SAMPLE_SIZE:
                            issue_samples[str(obj_id)] = {
                                #'orig_full': str(original_object),
                                #'adb_full': str(adb_object),
                                'diff': str(diff)
                            }
                orm.flush()
                orm.rollback()
        if affected_ids:
            LogService.Warning(f'ADB Disrepency found in {model.__name__} for [{len(affected_ids)}] objects', other_data={
                'affected_ids': affected_ids,
                'issue_samples': issue_samples
            })
        

    @classmethod
    def _objects_have_differences(cls, orig, adb, model):
        # Special values allow a difference of +1 as they change in time
        DIFFERENCE_VALUES = {
            'Contracts': ['days_since_contract_start', 'days_before_contract_payment_due', 'last_updated', 'payment_progression', 'expected_payment_progression'],
            'Issues': ['days_to_resolution'],
            'Leads': ['age'],
            'Clients': ['age']
        }
        IGNORE_VALUES = {
            'Contracts': ['par_status_group', 'expected_cumulative_amount_paid', 'cumulative_amount_in_arrears'],
            'Users': ['last_web_access', 'last_mobile_sync'],
            'Payments': ['payment_wallet_name'],
            'Reconciled_Payments': ['payment_wallet_name'],
            'Question_Answers': ['is_last_answer'],
            'Task_Types': ['linked_objects']
        }
        SENSITIVIVE_MODELS = ['Contracts', 'Clients', 'Leads', 'Issues'] # Those are updated daily at least
        model_name = model.__name__
        differences = {}
        for key, value in orig.items():
            val = adb.get(key, None)
            orig_val, adb_val = cls._get_comparable_values(value, val)
            if orig_val != adb_val:
                has_differences = True
                if key in IGNORE_VALUES.get(model_name, []):
                    has_differences = False
                if key in DIFFERENCE_VALUES.get(model_name, []):
                    if key == 'last_updated':
                        has_differences = False
                    else:
                        difference_number = 1
                        if 'days' in key:
                            difference_number = 2
                        if 'progression' in key:
                            difference_number = 0.01
                        adb_val_1, adb_val_2 = cls._get_comparable_values(val-difference_number, val+difference_number)
                        if adb_val_1 <= orig_val <= adb_val_2:
                            has_differences = False
                if has_differences:
                    differences[key] = {'orig': orig_val, 'adb': adb_val}
        if differences.get('last_updated', None):
            # In any case if it's only differences in last_updated we don't care
            if len(differences) == 1:
                return {}
            # We can usually safely ignore anything where last_updated doesnt match (except contracts)
            if (not cls.SENSITIVE_MODE) and model_name not in SENSITIVIVE_MODELS:
                last_updated = differences.get('last_updated')
                recent_update_threshold = datetime.now() - timedelta(hours=3)
                recent_update_threshold_adb = datetime.now() - timedelta(hours=24)
                # If the object has been updated in the last 24h in ADB and updated in the last 3h in Origin
                if datetime.fromisoformat(last_updated.get('orig')) > recent_update_threshold and datetime.fromisoformat(last_updated.get('adb')) > recent_update_threshold_adb:
                    return {}
        return differences
    
    @classmethod
    def _get_comparable_values(cls, value, val):
        # This normalises format that might slightly vary once stored in DB
        if isinstance(value, Decimal) or isinstance(value, float) or isinstance(value, int):
            # We normalize everything to 2 decimal places
            orig_val = Decimal("{:.2f}".format(round(value, 2))) if value is not None else None
            adb_val = Decimal("{:.2f}".format(round(val, 2))) if val is not None else None
        elif isinstance(value, list):
            # We use this for comparison not caring about the order
            orig_val = cls._get_comparable_list_of_dict(value)
            adb_val = cls._get_comparable_list_of_dict(val)
        else:
            # We compare everything else as string as they can be objects that can be mapped
            NULL_VALUES = [None, [], {}, 'None', '[]', '{}']
            orig_val = str(value) if value and value not in NULL_VALUES else None
            adb_val = str(val) if val and val not in NULL_VALUES else None
        return orig_val, adb_val
    
    @classmethod
    def _get_comparable_list_of_dict(cls, obj):
        if isinstance(obj, dict):
            return sorted((k, cls._get_comparable_list_of_dict(v)) for k, v in obj.items())
        if isinstance(obj, list):
            return sorted(cls._get_comparable_list_of_dict(x) for x in obj)
        else:
            return obj

    @classmethod
    def _get_up_to_date_objects_in_adb(cls, model):
        check_time = ModelUpdateService.get_last_update(model)
        return orm.select(obj for obj in model if obj.last_updated and obj.last_updated <= check_time)

    @classmethod
    @orm.db_session
    def _get_latest_updates_for_model(cls, model):
        latest_adb_update_metadata = ModelUpdateService.get_last_update(model)
        latest_adb_update_model = orm.max(obj.last_updated for obj in model)
        if not latest_adb_update_model:
                latest_adb_update_model = datetime.min
        latest_adb_update = min(latest_adb_update_metadata, latest_adb_update_model)
        latest_db_update = orm.max(model.extended_modified_date(obj) for obj in model.base_model)
        return latest_adb_update, latest_db_update