from pony.orm import Database
import config

if config.TEST_MODE:
    analytical_db = Database("sqlite", ':memory:', create_db=True)
else:
    analytical_db = Database("postgres", user=config.PG_USER, password=config.PG_PASSWORD,
                             host=config.ANALYTICAL_DB_HOST, port=config.ANALYTICAL_DB_PORT, database=config.ANALYTICAL_DB_NAME)