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
                port=port
            )
        except Exception as e:
            print(e)
            print('Could not get DB connection, retrying...')
            connection = None
        time.sleep(5)
    connection.autocommit = True
    return connection


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
    cur.execute("ALTER ROLE solaris_deploy SET statement_timeout='300s';")

def set_query_tracking_size(conn):
    print('Setting query tracking size...')
    cur = conn.cursor()
    cur.execute("ALTER SYSTEM SET track_activity_query_size = 16384;")


if __name__ == '__main__':
    print('Checking if DBs exists...')
    conn = get_postgres_connection()
    for db_name in (config.MAIN_DB_NAME, config.ACCOUNTING_DB_NAME, config.SMS_DB_NAME, config.AUDIT_DB_NAME):
        if not check_if_db_exist(conn, db_name):
            print(f'Creating DB {db_name}')
            create_db(conn, db_name)
    # We set the query timeout for the deploy user
    set_query_timeout(conn)
    # We set the query tracking query size to bigger size
    set_query_tracking_size(conn)
    print('Main DBs ready.')
    conn2 = get_postgres_connection(host=config.ANALYTICAL_DB_HOST, port=config.ANALYTICAL_DB_PORT)
    if not check_if_db_exist(conn2, 'analytical_db'):
            print(f'Creating DB analytical_db')
            create_db(conn2, 'analytical_db')
    print('Analytical DB ready.')