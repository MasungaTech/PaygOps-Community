import time
from core_system.core_entities import db
from shared.migrations.models import DatabaseVersion


class TestDatabaseVersion:
    def test_update_executed_migrations_set_versions(self):
        DatabaseVersion.update_executed_migrations(db, [1, 2])

        assert [1, 2] == DatabaseVersion.executed_migrations(db)

    def test_update_executed_migrations_set_versions_empty(self):
        DatabaseVersion.update_executed_migrations(db, [])

        assert [] == DatabaseVersion.executed_migrations(db)

    def test_is_pending_returns_true(self):
        timestamp = int(time.time())

        assert DatabaseVersion.is_pending(db, timestamp)

    def test_is_pending_returns_false(self):
        timestamp = int(time.time())
        DatabaseVersion.update_executed_migrations(db, [timestamp])

        assert DatabaseVersion.is_pending(db, timestamp) is False

    def test_rollback_migration(self):
        timestamp = int(time.time())
        DatabaseVersion.update_executed_migrations(db, [timestamp])

        DatabaseVersion.rollback_migration(db, timestamp)

        assert [] == DatabaseVersion.executed_migrations(db)

    def test_rollback_migration_with_invalid_version(self):
        timestamp = int(time.time())
        DatabaseVersion.update_executed_migrations(db, [timestamp])

        DatabaseVersion.rollback_migration(db, 1000)

        assert [timestamp] == DatabaseVersion.executed_migrations(db)

    def test_update_latest_migration(self):
        versions = [int(time.time()) for i in range(3)]
        latest_migration = versions[-1]

        DatabaseVersion.update_latest_version(db)

        assert latest_migration == DatabaseVersion.latest_version(db)

    def test_update_latest_migration_with_none_migrations(self):
        DatabaseVersion.update_executed_migrations(db, [])

        DatabaseVersion.update_latest_version(db)

        assert 0 == DatabaseVersion.latest_version(db)
