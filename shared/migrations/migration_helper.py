from datetime import datetime, time
from decimal import Decimal
import json
from pony.orm import *


PY_TYPES_TO_SQL = {
    str: 'text',
    int: 'int',
    datetime: 'datetime',
    float: 'float',
    time: 'time',
    bool: 'boolean',
    Json: 'json',
    Decimal: 'decimal'
}

KNOWN_DEFAULTS = {
    datetime.now: 'NOW()',
}

def get_default_from_property(default):
    if default is None:
        return
    if type(default) in [int, float, bool, str]:
        return default
    if isinstance(default, dict):
        return json.dumps(default)
    if default in KNOWN_DEFAULTS:
        return KNOWN_DEFAULTS[default]

def create_table_from_model(model, not_required_columns=[]):
    ''' Please only use this after checking the resulting sql is correct, not tested for all cases '''
    db = model._database_
    table = model._table_
    properties = model._attrs_
    indexes = model._indexes_

    create_table(db, table)
    for prop in properties:
        if prop.is_pk or not prop.column:
            continue
        add_column_from_model_property(prop, not_required_columns)
    for index in indexes:
        if len(index.attrs) < 2:
            continue
        if index.is_unique:
            add_composite_unique_constraint(db, table, *[a.column for a in index.attrs])
        else:
            add_composite_index(db, table, *[a.column for a in index.attrs])


def add_column_from_model_property(prop, not_required_columns=[]):
    db = prop.entity._database_
    table = prop.entity._table_
    add_column(
        db,
        table,
        prop.column,
        'int' if prop.is_relation else PY_TYPES_TO_SQL[prop.py_type],
        required=prop.is_required and prop.column not in not_required_columns,
        default=get_default_from_property(prop.default),
        unique=prop.is_unique,
    )
    if prop.is_relation:
        add_foreign_key_constraint(db, table, prop.column, prop.py_type._table_)


@db_session
def getDBVersion(mdb):
    try:
        version = int(mdb.execute("select current_setting('my.version') as version;").fetchone()[0])
    except ProgrammingError as e:
        print(e)
        version = 0
    print('The main database is @ ', version)
    return version


@db_session
def setDBVersion(mdb, version, db_name=None):
    if not db_name and hasattr(mdb, 'database'):
        db_name = mdb.database

    rollback()
    mdb.execute('set my.version to {version};'.format(version=version))
    mdb.execute('alter database {dbname} set my.version from current;'.format(dbname=db_name))
    print('The {dbname} is now set @ {version}'.format(version=version, dbname=db_name))
    commit()


SQLTYPES = {}
SQLTYPES['int'] = 'INTEGER'
SQLTYPES['datetime'] = 'TIMESTAMP without time zone'
SQLTYPES['text'] = 'TEXT'
SQLTYPES['float'] = 'REAL'
SQLTYPES['time'] = 'TIMESTAMP without time zone NOT NULL DEFAULT \'2001-01-01 00:00:00\'::timestamp without time zone'
SQLTYPES['time_null'] = 'TIMESTAMP without time zone'
SQLTYPES['boolean'] = 'boolean'
SQLTYPES['json'] = 'JSONB'
SQLTYPES['decimal'] = 'DECIMAL'
SQLTYPES['int[]'] = 'int[]'
SQLTYPES['text[]'] = 'text[]'

def change_default(db, tableName, variableName, default):
    db.execute(f"ALTER TABLE \"{tableName}\" ALTER COLUMN \"{variableName}\" SET DEFAULT {default};")


def add_column(db, tableName, variableName, type, required=False, default=None, unique=False, precision="12", scale="2", if_not_exists=True):
    ''' Available types: int, datetime, text, float, time, time_null, boolean, json, decimal, int[], text[]'''
    if if_not_exists:
        extra_command = 'IF NOT EXISTS '
    else:
        extra_command = ''
    this_query = "ALTER TABLE \"{tableName}\" ADD COLUMN {extra_command}\"{variableName}\" {type}".\
                format(tableName=tableName, variableName=variableName, type=SQLTYPES[type], extra_command=extra_command)
    if type == 'decimal':
        this_query += f'({precision},{scale})'

    if required:
        this_query += ' NOT NULL'
    if default is not None:
        if type == 'boolean':
            this_query += ' DEFAULT {}'.format(default)
        elif type == 'int':
            this_query += ' DEFAULT ' + str(default) + ''
        elif type == 'text':
            this_query += ' DEFAULT \'' + default + '\''
        elif type == 'json':
            this_query += ' DEFAULT \'' + default + '\''
        elif type == 'datetime' or type == 'decimal':
            this_query += ' DEFAULT ' + default
        else:
            this_query += ' DEFAULT "'+default+'"'

    print(this_query)
    db.execute(this_query)

    if unique:
        add_unique_constraint(db, tableName, variableName)


def create_table(db, table_name, with_id=True):
    params = ''

    if with_id:
        params = '(id serial NOT NULL PRIMARY KEY)'

    # no quotes for tablename so it raises an error if a keyword is used
    # by default non delimited identifiers (no quotes) are case insensitive
    # and the convention is to use lowercase names
    query = 'CREATE TABLE IF NOT EXISTS {} {}'.format(table_name, params)
    print(query)
    db.execute(query)

def sync_id_sequence(db, table):
    query = f"SELECT setval('{table}_id_seq', COALESCE((SELECT MAX(id)+1 FROM \"{table}\"), 1), false);"
    print(query)
    db.execute(query)
    
def drop_table(db, table_name):
    query = 'DROP TABLE IF EXISTS "{}" CASCADE '.format(table_name)
    print(query)

    db.execute(query)


def drop_column(db, table, column):
    query = 'ALTER TABLE "{}" DROP COLUMN IF EXISTS "{}"'.format(table, column)
    print(query)
    db.execute(query)


def set_primary_key(db, table_name, column):
    query = 'ALTER TABLE "{}" ADD PRIMARY KEY ({})'.format(table_name, column)
    db.execute(query)

def remove_primary_key(db, table_name):
    query = 'ALTER TABLE "{table}" DROP CONSTRAINT {table}_pkey CASCADE'.format(table=table_name)
    db.execute(query)
        
def remove_foreign_key_column(db, tableName, variableName):
    remove_foreign_key_constraint(db, tableName, variableName)
    drop_column(db, tableName, variableName)

def add_foreign_key_constraint(db, tableName, variableName, referenceTable, on_delete='null', if_not_exists=True, foreign_column='id'):
    if if_not_exists:
        remove_query = f'ALTER TABLE "{tableName}" DROP CONSTRAINT IF EXISTS "fk_{tableName}__{variableName}";'
        print(remove_query)
        db.execute(remove_query)
    this_query = 'ALTER TABLE "{tableName}" ADD CONSTRAINT "fk_{tableName}__{variableName}"'.\
                 format(tableName=tableName, variableName=variableName, referenceTable=referenceTable)

    this_query += f' FOREIGN KEY ("{variableName}") REFERENCES "{referenceTable}" ("{foreign_column}")'.\
                 format(variableName=variableName, referenceTable=referenceTable, foreign_column=foreign_column)
                 
    if on_delete == 'null':
        this_query += ' ON DELETE SET NULL'
    elif on_delete == 'default':
        this_query += ' ON DELETE SET DEFAULT'
    elif on_delete == 'cascade':
        this_query += ' ON DELETE CASCADE'
    elif on_delete == 'noaction':
        this_query += ' ON DELETE NO ACTION'
    else:
        this_query += ' ON DELETE RESTRICT'
        
    print(this_query)
    db.execute(this_query)


def add_fk_column(
        db, table_name, column_name, reference_table,
        on_delete='null', if_not_exists=True, required=False
    ):
    add_column(db, table_name, column_name, "int", required=required)
    add_foreign_key_constraint(
        db, table_name, column_name,
        reference_table, on_delete, if_not_exists
    )

def remove_foreign_key_constraint(db, tableName, variableName):
    query = f"ALTER TABLE \"{tableName}\" DROP CONSTRAINT IF EXISTS \"fk_{tableName}__{variableName}\""
    print(query)
    db.execute(query)


def add_index(db, tableName, variableName):
    thisQuery = 'CREATE INDEX IF NOT EXISTS "idx_{tableNameSmall}__{variableNameSmall}" ON "{tableName}" ("{variableName}")'.\
                 format(tableNameSmall=tableName.lower(), variableNameSmall=variableName.lower(),
                        tableName=tableName, variableName=variableName)
    print(thisQuery)
    db.execute(thisQuery)

def add_composite_index(db, tableName, *vars):
    thisQuery = 'CREATE INDEX IF NOT EXISTS "idx_{tableNameSmall}__{variableNameSmall}" ON "{tableName}" ("{variableName}")'.\
                 format(tableNameSmall=tableName.lower(), variableNameSmall='_'.join(vars).lower(),
                        tableName=tableName, variableName='", "'.join(vars).lower())
    print(thisQuery)
    db.execute(thisQuery)


def add_gist_index(db, tableName, variableName):
    thisQuery = 'CREATE INDEX IF NOT EXISTS "idx_{tableNameSmall}__{variableNameSmall}_gist" ON "{tableName}" USING gist ("{variableName}" gist_trgm_ops)'.\
                 format(tableNameSmall=tableName.lower(), variableNameSmall=variableName.lower(),
                        tableName=tableName, variableName=variableName)
    print(thisQuery)
    db.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm;') # Needed to install the proper index tool
    db.execute(thisQuery)


def remove_index(db, tableName, variableName):
    query = "DROP INDEX IF EXISTS idx_{0}__{1}".format(tableName.lower(), variableName.lower())
    print(query)
    db.execute(query)

def remove_index_by_name(db, name):
    query = "DROP INDEX IF EXISTS {0}".format(name)
    print(query)
    db.execute(query)


@db_session
def addModifiedDateColumnForPostgres(database, tableName):
    first_query = "ALTER TABLE \"{table_name}\" ADD COLUMN modified_date timestamp without time zone NOT NULL DEFAULT '2001-01-01 00:00:00'::timestamp without time zone;".format(table_name=tableName)

    database.execute(first_query)
    commit()


def add_unique_constraint(db, table, column):
    query = "ALTER TABLE \"{}\" ADD UNIQUE (\"{}\")".format(table, column)
    print(query)
    db.execute(query)

def remove_unique_constraint(db, table, column):
    query = "ALTER TABLE \"{table}\" DROP CONSTRAINT IF EXISTS {table}_{column}_key".format(table=table, column=column)
    print(query)
    db.execute(query)

def add_composite_unique_constraint(db, table, *columns):
    names = '_'.join(columns)
    quoted = '", "'.join(columns)
    query = "ALTER TABLE {0} ADD CONSTRAINT unq_{0}__{1} UNIQUE (\"{2}\")".format(table, names, quoted)
    print(query)
    db.execute(query)

def remove_composite_unique_constraint(db, table, *columns):
    names = '_'.join(columns)
    query = "ALTER TABLE {0} DROP CONSTRAINT IF EXISTS unq_{0}__{1}".format(table, names)
    print(query)
    db.execute(query)
    query = "DROP INDEX IF EXISTS unq_{0}__{1}".format(table, names)
    print(query)
    db.execute(query)

def remove_composite_index(db, table, column1, column2):
    query = "DROP INDEX unq_{0}__{1}_{2}".format(table,column1,column2)
    print(query)
    db.execute(query)

def column_required_to_optional(db, table, column):
    query = 'ALTER TABLE \"{}\" ALTER COLUMN "{}" DROP NOT NULL;'.format(table.lower(), column)
    print(query)
    db.execute(query)


def column_optional_to_required(db, table, column):
    query = 'ALTER TABLE "{}" ALTER COLUMN "{}" SET NOT NULL;'.format(table, column)
    db.execute(query)
    print(query)


def add_auto_primary_key(db, table_name, column):
    query = 'ALTER TABLE "{}" ADD COLUMN IF NOT EXISTS "{}" SERIAL PRIMARY KEY;'.format(table_name, column)
    db.execute(query)


def alter_column_type(db, table_name, column, new_type):
    query = 'ALTER TABLE "{}" ALTER COLUMN "{}" SET DATA TYPE {};'.format(table_name, column, new_type)
    db.execute(query)

def rename_column(db, table_name, old_column_name, new_column_name):
    query = f'ALTER TABLE "{table_name}" RENAME COLUMN "{old_column_name}" TO "{new_column_name}";'
    db.execute(query)

def rename_table(db, table_name, new_table_name):
    query = f'ALTER TABLE "{table_name}" RENAME TO "{new_table_name}";'
    db.execute(query)

def set_column_default(db, table, column, default):
    query = 'ALTER TABLE "{}" ALTER COLUMN "{}" SET DEFAULT {};'.format(table, column, default)
    db.execute(query)
    print(query)

def change_numeric_scale(db, table, column, precision=12, scale=2):
    query = 'ALTER TABLE "{}" ALTER COLUMN "{}" TYPE DECIMAL({},{});'.format(table, column, precision, scale)
    db.execute(query)
    print(query)


def create_intermediate_table(db, table1, table2, column1=None, column2=None, table_name=None):
    ts = sorted([(table1, column1 or table1), (table2, column2 or table2)], key=lambda x: x[0])
    table_name = table_name or '_'.join([t[0] for t in ts])
    create_table(db, table_name)
    add_column(db, table_name, ts[0][1], 'int', required=True)
    add_foreign_key_constraint(db, table_name, ts[0][1], ts[0][0])
    add_column(db, table_name, ts[1][1], 'int', required=True)
    add_foreign_key_constraint(db, table_name, ts[1][1], ts[1][0])
    return table_name

def drop_intermediate_table(db, table1=None, table2=None, table_name=None):
    ts = sorted([table1, table2])
    table_name = table_name or '_'.join(ts)
    drop_table(db, table_name)

def safe_add_colum(db, table, column, type, default=None):
    try:
        add_column(db, table, column, type, default=default)
    except OperationalError as error:
        if not 'duplicate column name' in str(error) or 'does not exist' in str(error):
            raise error