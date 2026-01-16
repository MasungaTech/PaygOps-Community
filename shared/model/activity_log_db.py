from pony import orm
from config import TEST_MODE, PG_USER, PG_PASSWORD, PG_HOST, PG_PORT


if TEST_MODE:
    audit_db = orm.Database("sqlite", ':memory:', create_db=True)
else:
    audit_db = orm.Database("postgres", user=PG_USER, password=PG_PASSWORD, host=PG_HOST, port=PG_PORT, database='audit_db')

