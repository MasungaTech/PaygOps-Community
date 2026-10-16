import math
from pony import orm
from psycopg2.errors import ForeignKeyViolation
from shared.helpers.db_helpers import set_transaction_readonly
from core_system.core_entities import db as main_db
from shared.logger.loggers import LogService
from data_system.analytical_db.analytical_db import Metadata, analytical_db
from datetime import datetime
from psycopg2.extras import execute_values
import config
import re
import gc


class ModelUpdateService:

    PAGE_SIZE_CAT = {
        5: 10000,
        4: 1000,
        3: 100,
        2: 25,
        1: 1
    }

    @classmethod
    def update_model_objects(cls, model, to_delete_ids=None, to_insert_ids=None, to_update_ids=None, **kwargs):

        to_delete_ids = to_delete_ids or []
        to_insert_ids = to_insert_ids or []
        to_update_ids = to_update_ids or []

        # We reduce the bigger page sizes on smaller servers to save RAM
        if config.GLOBAL_SCALE < 8:
            cls.PAGE_SIZE_CAT = {
                5: 2500,
                4: 250,
                3: 50,
                2: 25,
                1: 1
            }
        
        # Any kwargs is passed to the converter as needed
        print(f'{model.__name__} - Del: {len(to_delete_ids)}, Ins: {len(to_insert_ids)}, Upd: {len(to_update_ids)}')
        page_size_cat = model.default_page_size_cat() if model.default_page_size_cat() else 5
        failed_delete = cls._process_object_ids(model, to_delete_ids, page_size_cat, action='delete', **kwargs) # Always first
        failed_insert = cls._process_object_ids(model, to_insert_ids, page_size_cat, action='insert', **kwargs)
        failed_update = cls._process_object_ids(model, to_update_ids, page_size_cat, action='update', **kwargs)
        if failed_delete or failed_insert or failed_update:
            LogService.Warning(
                f'Issue when generating the analytical db for [{model.__name__}]: [{len(failed_delete)+len(failed_insert)+len(failed_update)}] objects affected', 
                other_data={
                    'failed_delete': failed_delete,
                    'failed_insert': failed_insert,
                    'failed_update': failed_update
                }
            )

    @classmethod
    def _process_object_ids(cls, model, object_ids, page_size_cat, action, retrying=False, objects=None, **kwargs):
        failed_objects = []
        processed = 0
        page_size = cls.PAGE_SIZE_CAT[page_size_cat]
        page = 1
        for page_ids in cls._get_pages(object_ids, page_size):
            try:
                if objects: page_objects = cls._get_page(objects, page_size, page)
                else: page_objects = cls._load_objects(model, page_ids, **kwargs)
            except Exception as e:
                LogService.FatalNoRequest(e)
                page_objects = None
            try:
                try:
                    cls._process_objects(model, page_ids, action, retrying=retrying, objects=page_objects, **kwargs)
                except (ForeignKeyViolation, orm.TransactionIntegrityError) as e:
                    if page_size_cat == 1:
                        cls._process_fk_violation(e)
                        cls._process_objects(model, page_ids, action, retrying=retrying, objects=page_objects, **kwargs)
                    else: 
                        raise e
            except Exception as e:
                if page_size_cat == 1:
                    failed_objects += page_ids
                    LogService.FatalNoRequest(e, raise_if_test=True)
                    cls._set_objects_failed(model, page_ids, **kwargs)
                else:
                    if config.TEST_MODE:
                        LogService.Event('ERROR DURING FIRST SAVE: '+str(e))
                    page_size_cat_sub = page_size_cat - 1
                    failed_objects += cls._process_object_ids(model, page_ids, page_size_cat_sub, action, retrying=True, objects=page_objects, **kwargs)
            processed += len(page_ids)
            page+=1
            print(f'{processed} {model.__name__} {action}ed')
        return failed_objects

    @classmethod
    def _process_fk_violation(cls, error):
        error_string = str(error)+' '+str(error.args)
        ERROR_PATTERN = r'Key \([a-z_]+\)=\(([0-9]+)\) is not present in table "([a-zA-z_]+)"'
        matches = re.search(ERROR_PATTERN, error_string, re.IGNORECASE)
        if matches:
            object_id = matches.group(1)
            model_name = matches.group(2)
            from data_system.analytical_db.services.update_service import AnalyticalDBUpdateService
            model = None
            for m in AnalyticalDBUpdateService.MODELS:
                if m._table_ == model_name:
                    model = m
            if model:
                try:
                    cls._process_objects(model, [int(object_id)], 'insert')
                    return
                except (ForeignKeyViolation, orm.TransactionIntegrityError) as e1:
                    cls._process_fk_violation(e1)
                    try:
                        cls._process_objects(model, [int(object_id)], 'insert')
                        return
                    except (ForeignKeyViolation, orm.TransactionIntegrityError) as e2:
                        cls._process_fk_violation(e2) # We got to N+2 as it is quite common
                        cls._process_objects(model, [int(object_id)], 'insert')
                        return
        raise error

    @classmethod
    def _get_pages(cls, ids, page_size):
        number_of_pages = math.ceil(len(ids) / page_size)
        pages = []
        for page in range(1, number_of_pages + 1):
            pages.append(cls._get_page(ids, page_size, page))
        return pages
    
    @classmethod
    def _get_page(cls, data, page_size, page):
        return data[(page - 1) * page_size: page * page_size]

    @classmethod
    def _get_objects_by_id(cls, model, object_ids):
        objects = model.base_model.select(lambda o: o.id in object_ids)
        return model.selector(objects)

    @classmethod
    def _load_objects(cls, model, page_ids, **kwargs):
        with orm.db_session(optimistic=False):
            set_transaction_readonly(main_db)
            objects = cls._get_objects_by_id(model, page_ids)
            object_data = [model.converter(obj, **kwargs) for obj in objects]
            orm.rollback()
        return object_data

    @staticmethod
    def _load_sets(obj, set_model):
        for set_name, model in set_model.items():
            raw_set_name = set_name+'_set'
            obj[set_name] = orm.select(set_obj for set_obj in model if set_obj.id in obj[raw_set_name])
            obj.pop(raw_set_name)
        return obj

    @classmethod
    def test_bulk_forbidden(cls, model):
        # This is a workaround to avoid the issue of Decimal conversion in SQLite
        return config.TEST_MODE and model.__name__.lower() in ['contracts' ,'contractpayments']

    @classmethod
    def _process_objects(cls, model, page_ids, action, retrying=False, objects=None, **kwargs):
        if len(page_ids) == 0:
            return
        if retrying and action == 'insert':
            action = 'upsert'
        if action == 'delete':
            with orm.db_session(optimistic=False):
                orm.select(o for o in model if o.id in page_ids).delete(bulk=True)
                orm.commit()
        else:
            if not objects:
                print('Getting objects again')
                objects = cls._load_objects(model, page_ids, **kwargs)
            with orm.db_session(optimistic=False):
                # We do that to load the proper object in analytical DB in case of Sets
                # This must be in the same DB session as the writing
                set_converter = model.get_set_converter()
                if set_converter:
                    objects = [cls._load_sets(obj, set_converter) for obj in objects]
                if action == 'insert':
                    if model.bulk_allowed() and not cls.test_bulk_forbidden(model):
                        cls._bulk_insert(model, objects)
                    else:
                        for obj in objects:
                            model(**obj)
                elif action == 'update':
                    if model.bulk_allowed() and not cls.test_bulk_forbidden(model):
                        cls._bulk_update(model, objects)
                    else:
                        for obj in objects:
                            model.get(id=obj['id']).set(**obj)
                elif action == 'upsert':
                    for obj in objects:
                        this_obj = model.get(id=obj['id'])
                        if this_obj:
                            this_obj.set(**obj)
                        else:
                            model(**obj)
                else:
                    raise Exception(f'Unknown action: {action}')
                last_obj = objects.pop() if objects else None
                if last_obj:
                    print('Setting last updated time to '+str(last_obj['last_updated']))
                    cls._get_metadata_object(model).get(table=model._table_).updated_on = last_obj['last_updated']
                orm.commit()
                orm.rollback()
            del objects
            gc.collect()
    
    @classmethod
    def _set_objects_failed(cls, model, object_ids, **kwargs):
        for obj_id in object_ids:
            # Contract stats historical have a special ID format
            if model.__name__ in ['OldContractStatsHistorical', 'ContractStatsHistorical', 'Contracts_History']:
                obj_id = f'{kwargs.get("to_date"):%Y-%m-%d}-{obj_id}'
            with orm.db_session(optimistic=False):
                obj = model.get(id=obj_id)
                if obj:
                    obj.last_updated = None
                    orm.commit()
                else:
                    model(id=obj_id, last_updated=None) # We create an empty object to avoid FK issues
                    orm.commit()

    @classmethod
    def _bulk_insert(cls, table, objects):
        if len(objects) == 0:
            return
        if config.TEST_MODE:
            cls._bulk_insert_sqlite(table, objects, adb=analytical_db)
        else:
            cls._bulk_insert_pg(table, objects)

    @classmethod
    def _bulk_insert_sqlite(cls, table, objects, adb):
        fields = [key for key,value in objects[0].items()]
        sql = f'INSERT INTO "{table._table_}"({",".join(fields)}) VALUES ({",".join(["?" for x in range(0, len(objects[0]))])})'
        value_array = [cls._value_list_insert(obj) for obj in objects]
        con = adb.get_connection()
        con.executemany(sql, value_array)
    
    @classmethod
    def _bulk_insert_pg(cls, table, objects):
        fields = [key for key,value in objects[0].items()]
        sql = f'INSERT INTO "{table._table_}"({",".join(fields)}) VALUES %s'
        value_array = [cls._value_list_insert(obj) for obj in objects]
        con = analytical_db.get_connection()
        cur = con.cursor()
        execute_values(cur, sql, value_array)

    @classmethod
    def _bulk_update(cls, table, objects):
        if config.TEST_MODE:
            cls._bulk_update_sqlite(table, objects, adb=analytical_db)
        else:
            cls._bulk_update_pg(table, objects)

    @classmethod
    def _bulk_update_sqlite(cls, table, objects, adb):
        if not objects:
            return
        fields = [key for key,value in objects[0].items() if key != 'id']
        sql = f'UPDATE "{table._table_}" SET {" = ?, ".join(fields)} = ? WHERE id = ?'
        value_array = [cls._value_list_update(obj) for obj in objects]
        con = adb.get_connection()
        con.executemany(sql, value_array)

    @classmethod
    def _bulk_update_pg(cls, table, objects):
        if not objects:
            return
        fields = [key for key,value in objects[0].items() if key != 'id']
        sql = f'UPDATE {table._table_} SET {",".join(f"{key} = d.{key}" for key in fields)} FROM (VALUES %s) AS d (id,{",".join(fields)}) WHERE {table._table_}.id = d.id'
        value_array = [cls._value_list_insert(obj) for obj in objects]
        con = analytical_db.get_connection()
        cur = con.cursor()
        execute_values(cur, sql, value_array, template=cls._get_typed_fields_template(table, fields))

    @classmethod
    def _get_typed_fields_template(cls, table, fields):
        typed_fields = []
        for field in fields:
            sql_type = getattr(table, field).converters[0].get_sql_type()
            typed_fields.append(f'%s::{sql_type.lower()}')
        return '(%s,'+','.join(typed_fields)+')'

    @classmethod
    def _value_list_insert(cls, this_object):
        return [value for key,value in this_object.items()]
    
    @classmethod
    def _value_list_update(cls, this_object):
        values = [value for key,value in this_object.items()]
        return values[1:] + [values[0]] # We put the ID last

    @classmethod
    def get_last_update(cls, model):
        table = model._table_
        meta = cls._get_metadata_object(model)
        metadata_entry = meta.get(table=table)
        if not metadata_entry:
            metadata_entry = meta(table=table, updated_on=datetime.min)
            print(f'{model.__name__}: Table not found in Analytical DB. Copying all data.')
        else:
            print(f'Last updated on: {metadata_entry.updated_on}')
        return metadata_entry.updated_on

    @classmethod
    def _get_metadata_object(cls, model):
        return Metadata
        