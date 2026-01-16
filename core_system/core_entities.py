from pony.orm import *
from config import TEST_MODE, PG_USER, PG_PASSWORD, PG_HOST, PG_PORT, MAIN_PG_HOST, MAIN_PG_PORT


if TEST_MODE:
    db = Database("sqlite", ':memory:', create_db=True)

elif not TEST_MODE:
    db = Database("postgres", user=PG_USER, password=PG_PASSWORD, host=MAIN_PG_HOST, port=MAIN_PG_PORT, database='main_db')

#sql_debug(True)
