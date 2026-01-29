import config
from shared.logger.loggers import LogService
from pony import orm
from core_system.core_entities import db as mdb
from accounting_system.accounting_db import accounting_db
from messages_system.models.sms_db import sms_db
from shared.migrations.initial_setup.configure import create_default_offer


def set_db_version():
    from shared.migrations.migration_helper import setDBVersion
    try:
        print('Setting DB version...')
        setDBVersion(mdb, config.latest_main_db_version_pg, 'main_db')
        setDBVersion(accounting_db, config.latest_accounting_db_version_pg, 'accounting_db')
        setDBVersion(sms_db, config.latest_sms_db_version_pg, 'sms_db')
        orm.commit()
    except Exception as e:
        LogService.Fatal(e)


def create_tables():
    from web_app import app # This calls the generate mapping function
    print(app)
    print('Created tables.')
    

@orm.db_session
def db_initialized():
    try:
        conn = mdb.get_connection()
        cur = conn.cursor()
        cur.execute('SELECT id from public.user where id = 1;')
        return cur.fetchone()
    except Exception as e:
        if 'relation "public.user" does not exist' in str(e):
            return False
        else:
            LogService.Fatal(e)


def configure():
    from shared.migrations.initial_setup.configure import create_admin_user, \
        create_system_surveys, create_default_accounts, \
        create_default_interaction_and_issue_topics, create_default_locations, \
        create_default_lead_statuses, create_default_addons_categories, \
        create_default_lead_generator, create_default_lead_generator_types
    from core_system.role.migrations.install_permissions import install_permissions
    from web_app import app
    from sales_system.install import create_reasons_for_not_buying

    try:
        print('Configuring permissions...')
        install_permissions()
        print('Creating a default user...')
        create_admin_user()
        print('Creating default locations...')
        create_default_locations()
        print('Creating the system Surveys...')
        create_system_surveys()
        print('Creating the default Discussion Topics...')
        create_default_interaction_and_issue_topics()
        print('Creating the default Accounts...')
        create_default_accounts()
        print('Creating the Reasons for not buying...')
        create_reasons_for_not_buying()
        print('Creating lead statuses...')
        create_default_lead_statuses()
        print('Create addons categories...')
        create_default_addons_categories()
        print('create default lead generator types')
        create_default_lead_generator_types()
        print('create default lead generator')
        create_default_lead_generator()
        print('create default ticketing offer')
        create_default_offer()
        print('Creating settings...')
        with orm.db_session:
            from shared.services.settings_service import SettingsService
            SettingsService.set_defaults()
        orm.commit()
    except Exception as e:
        LogService.Fatal(e)


if __name__ == '__main__':
    if not db_initialized():
        print('Initiliazing DB...')
        create_tables()
        set_db_version()
        from shared.migrations.commands.migrate import install
        install(1) # This is to set the db version
        configure()
    else:
        print('DB initialized already.')
    