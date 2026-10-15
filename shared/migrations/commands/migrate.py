from os import listdir, chmod
import stat
import time
import importlib.util
from os.path import join, exists
from pony.orm import db_session
from core_system.core_entities import db
from shared.migrations.models import DatabaseVersion
from config import MIGRATIONS_DIR
from pony import orm
from shared.logger.loggers import LogAPI


IGNORE_FILES = [
    'migration_helper.py',
    '__init__.py',
    'models.py']



def install(version):
    versions = [get_version(f) for f in get_files()]

    DatabaseVersion.create_version_table(db)
    DatabaseVersion.set_version(db, versions[-1])
    DatabaseVersion.update_executed_migrations(db, versions)


def uninstall():
    DatabaseVersion.remove_version_table(db)


def set_db_version(version):
    set_version(version)


def up(depth=0):

    last_error = None
    for module_name in get_files():
        version = get_version(module_name)

        if DatabaseVersion.is_pending(db, version):
            last_error = migrate_up(module_name)

    if not DatabaseVersion.executed_migrations(db):
        versions = []

        for module_name in get_files():
            versions.append(get_version(module_name))

        DatabaseVersion.update_executed_migrations(db, versions)

    if len(get_pending()) > 0:
        if depth > 3:
            print('Recursion error, migrations failed after 4 attempts')
            raise Exception('Migration recursion limit exceeded.') from last_error
        up(depth=depth+1)


def down(version):
    if version is None:
        print('Please specify a version revert.')
        return

    version = int(version)

    for module_name in get_files():
        if version == get_version(module_name):
            migrate_down(module_name, version)
            break


def migrate_up(module_name, non_check=False):
    version = get_version(module_name)

    if non_check or DatabaseVersion.is_pending(db, version):
        try:
            print('Running migration', module_name)
            migration = get_module(module_name)
            migration.up(db)
        except Exception as e:
            LogAPI().FatalNoRequest(e)
            LogAPI().FatalNoRequest(Exception(f'Migration {module_name} failed: '+str(e)))
            orm.rollback()
            print('Was not possible to migrate', module_name, str(e), e.args)
            return e
        else:
            set_version(version)
            orm.commit()
            print('Success with', module_name)
    else:
        print('Migratios are up to date')


def migrate_down(module_name, version):
    try:
        migration = get_module(module_name)
        migration.down(db)
        DatabaseVersion.rollback_migration(db, version)
        DatabaseVersion.update_latest_version(db)
        print('Rollback migration {}'.format(module_name))
    except AttributeError:
        print('down function is not implemented in {}'.format(module_name))


def create_migration(name,
                     migrations_dir=MIGRATIONS_DIR,
                     version=None):

    if version is None:
        version = latest_version() + 1

    file_name = '{}{}_{}.py'.format(migrations_dir, version, name)
    template = "from pony.orm import db_session\n\n" \
               "@db_session\ndef up(db):\n    pass\n\n" \
               "@db_session\ndef down(db):\n    pass\n"

    with open(file_name, 'w+') as f:
        f.write(template)

    if exists(file_name):
        chmod(file_name, stat.S_IRWXO)
        print('Migration file {} was created.'.format(file_name.replace('/crm/', '', 1)))


def get_files():
    files = [
        f.replace('.py', '') for f in listdir(MIGRATIONS_DIR) if is_valid(f)]

    return sorted(files, key=get_version)


def get_pending():
    return [f for f in get_files() if DatabaseVersion.is_pending(db, get_version(f))]


def is_valid(file):
    return file.endswith('.py') and file not in IGNORE_FILES


def set_version(version):
    DatabaseVersion.set_version(db, version)


def get_version(file_name):
    try:
        return int(file_name.split('_')[0])
    except Exception:
        return latest_version()


def check_version(version):
    return version > latest_version()


@db_session
def latest_version():
    return DatabaseVersion.latest_version(db)


def get_module(module):
    path_module = join(MIGRATIONS_DIR, f'{module}.py')
    spec = importlib.util.spec_from_file_location(module, path_module)
    if spec is None or spec.loader is None:
        raise ImportError(f'Could not load migration module: {module}')
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration
