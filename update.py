from shared.logger.loggers import LogAPI
import config


logger = LogAPI()

class BadDefinitionError(Exception):
    pass


if __name__ == "__main__":
    # migrate
    try:
        from web_app.registerer import BlueprintRegisterer
        from shared.migrations.commands.migrate import up
        up()
    except Exception as e:
        print(f'Exception "{e}", retrying...')
        try:
            from shared.migrations.commands.migrate import up
            up()
        except Exception as e:
            logger.FatalNoRequest(e)
    # set_permissions
    try:
        from web_app.registerer import BlueprintRegisterer
        from core_system.role.migrations.update_permissions import update_permissions
        update_permissions()
    except Exception as e:
        logger.FatalNoRequest(e)
    # Update reasons for not buying
    try:
        from sales_system.install import create_reasons_for_not_buying
        create_reasons_for_not_buying()
    except Exception as e:
        logger.FatalNoRequest(e)
    # Update settings
    try:
        from shared.services.settings_service import SettingsService
        from pony import orm
        with orm.db_session:
            SettingsService.set_defaults()
    except Exception as e:
        logger.FatalNoRequest(e)

    try:
        print('Updating Analytical DB metadata...')
        from data_system.analytical_db.analytical_db import analytical_db
        analytical_db.generate_mapping(create_tables=True)
        with orm.db_session:
            for entity in analytical_db.entities.values():
                table = entity._table_
                if entity._description_:
                    description = entity._description_.replace("'", "''") # The double quote is the way to escape quotes in Postgres string
                    try:
                        analytical_db.execute(f"COMMENT ON TABLE {table} IS '{description}'")
                    except AttributeError:
                        raise BadDefinitionError(f'{entity.__name__} has no _description_ attribute (must inherit from BaseAnalyticalDBModel)')
                for attr in entity._attrs_:
                    if not attr.column or not attr.comment:
                        continue
                    comment = attr.comment.replace("'", "''") # The double quote is the way to escape quotes in Postgres strings
                    try:
                        analytical_db.execute(f"COMMENT ON COLUMN {table}.{attr.column} IS '{comment}'")
                    except AttributeError:
                        raise BadDefinitionError(f'{attr} does not use the extended Attribute classes with support for comments')
        print('Analytical DB metadata updated')
    except BadDefinitionError as e:
        if config.ENV_VAR in ['TEST', 'DEV']:
            raise e
        logger.FatalNoRequest(e)
    except Exception as e:
        logger.FatalNoRequest(e)