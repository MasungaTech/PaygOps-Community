from pony.orm import db_session

from core_system.phone_numbers.services.phone_number_cleanup_service import \
    PhoneNumberCleanupService


@db_session
def up(db):
    PhoneNumberCleanupService.cleanup_unassigned_phone_numbers()


@db_session
def down(db):
    pass
