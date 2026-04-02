import os
import tempfile
from shared.migrations.commands.migrate import set_version, latest_version, \
                                        check_version, get_version,\
                                        create_migration, is_valid

tmp_dir = tempfile.mkdtemp()

VERSION_FILE = tmp_dir + '/.test_migration_version'


def test_is_valid_returns_false():
    assert is_valid('migration_helper.py') is False
    assert is_valid('migration_helper') is False


def test_is_valid_returns_true():
    assert is_valid('my_migration_1.py')


def test_set_version():
    set_version(1)

    assert 1 == latest_version()


def test_latest_version():
    set_version(1)

    assert 1 == latest_version()


def test_check_version_returns_false():
    set_version(2)

    assert check_version(1) is False


def test_check_version_returns_true():
    set_version(1)

    assert check_version(2)


def test_get_version_returns_one():
    assert 1 == get_version('my_migration_1')


def test_get_version_returns_latest():
    set_version(2)

    assert 2 == get_version('my_migration_test')


def test_create_migration():
    set_version(1)
    file = tmp_dir + r'/2_run_test.py'
    create_migration('run_test', migrations_dir=tmp_dir+'/')

    assert os.path.exists(file)

    os.remove(file)
