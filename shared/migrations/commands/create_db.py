import config
import time


def get_postgres_connection(dbname='postgres', user=config.PG_USER, password=config.PG_PASSWORD, host=config.PG_HOST, port=config.PG_PORT):
    import psycopg2
    connection = None
    while not connection:
        try:
            connection = psycopg2.connect(
                database=dbname,
                user=user,
                password=password,
                host=host,
                port=port,
                connect_timeout=30,
            )
        except Exception as e:
            print(e)
            print('Could not get DB connection, retrying...')
            connection = None
        time.sleep(5)
    connection.autocommit = True
    return connection


def try_direct_connection(dbname, user, password, host, port):
    """Try once to open a connection to the target database (e.g. already provisioned on DO)."""
    import psycopg2
    try:
        conn = psycopg2.connect(
            database=dbname,
            user=user,
            password=password,
            host=host,
            port=port,
            connect_timeout=30,
        )
        conn.close()
        return True
    except Exception as e:
        print(f'Direct connection to database "{dbname}" failed: {e}')
        return False


def check_if_db_exist(conn, database_name):
    cur = conn.cursor()
    cur.execute("SELECT datname FROM pg_database;")
    list_database = cur.fetchall()
    if (database_name,) in list_database:
        return True
    else:
        return False


def create_db(conn, database_name):
    print('Creating DB...')
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE {database_name};")


def set_query_timeout(conn):
    print('Setting query timeout...')
    cur = conn.cursor()
    cur.execute('ALTER ROLE solaris_deploy SET statement_timeout=\'300s\';')


def set_query_tracking_size(conn):
    print('Setting query tracking size...')
    cur = conn.cursor()
    cur.execute("ALTER SYSTEM SET track_activity_query_size = 16384;")


if __name__ == '__main__':
    print('Checking databases (direct connect first, then create if needed)...')
    main_db_names = dict.fromkeys((
        config.MAIN_DB_NAME,
        config.ACCOUNTING_DB_NAME,
        config.SMS_DB_NAME,
        config.AUDIT_DB_NAME,
    ))
    conn_postgres = None
    for db_name in main_db_names:
        if try_direct_connection(db_name, config.PG_USER, config.PG_PASSWORD, config.PG_HOST, config.PG_PORT):
            print(f'Database "{db_name}" is reachable (skipping create).')
            continue
        if conn_postgres is None:
            conn_postgres = get_postgres_connection()
        if not check_if_db_exist(conn_postgres, db_name):
            print(f'Creating DB {db_name}')
            create_db(conn_postgres, db_name)
        else:
            print(f'Database "{db_name}" already exists (could not use direct connection earlier).')

    if conn_postgres is not None:
        try:
            set_query_timeout(conn_postgres)
        except Exception as e:
            print(f'Skipping query timeout (not permitted or not applicable): {e}')
        try:
            set_query_tracking_size(conn_postgres)
        except Exception as e:
            print(f'Skipping track_activity_query_size (not permitted or not applicable): {e}')
    print('Main DBs ready.')

    if try_direct_connection(
        config.ANALYTICAL_DB_NAME,
        config.PG_USER,
        config.PG_PASSWORD,
        config.ANALYTICAL_DB_HOST,
        config.ANALYTICAL_DB_PORT,
    ):
        print(f'Analytical database "{config.ANALYTICAL_DB_NAME}" is reachable (skipping create).')
    else:
        conn2 = get_postgres_connection(host=config.ANALYTICAL_DB_HOST, port=config.ANALYTICAL_DB_PORT)
        if not check_if_db_exist(conn2, config.ANALYTICAL_DB_NAME):
            print(f'Creating DB {config.ANALYTICAL_DB_NAME}')
            create_db(conn2, config.ANALYTICAL_DB_NAME)
        else:
            print(f'Database "{config.ANALYTICAL_DB_NAME}" already exists (could not use direct connection earlier).')
    print('Analytical DB ready.')
