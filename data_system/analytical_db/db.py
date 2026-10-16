from pony.orm import Database
import config

if config.TEST_MODE:
    analytical_db = Database("sqlite", ':memory:', create_db=True)
else:
    analytical_db = Database("postgres", user=config.ANALYTICAL_DB_USER, password=config.ANALYTICAL_DB_PASSWORD,
                             host=config.ANALYTICAL_DB_HOST, port=config.ANALYTICAL_DB_PORT, database=config.ANALYTICAL_DB_NAME)