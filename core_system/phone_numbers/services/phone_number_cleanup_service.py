from pony import orm

from core_system.person.models.person_model import Person
from core_system.phone_numbers.model import PhoneNumbers
from shared.helpers.chunk_executer import isolated_chunk_executer
from shared.logger.loggers import LogAPI


class PhoneNumberCleanupService:
    """Unlink leftover owner mappings so unassigned numbers are not searchable.

    Phone number rows are never deleted.
    """

    @classmethod
    def cleanup_unassigned_phone_numbers(cls):
        cls._sync_contact_phone_into_persons()
        cls._unlink_orphaned_persons()
        cls._clear_stale_legacy_person_links()

    @classmethod
    def unlink_person(cls, phone_number, person):
        if not phone_number or not person:
            return
        if person.contactPhone == phone_number:
            person.contactPhone = None
        if person in phone_number.persons:
            phone_number.persons.remove(person)
        if phone_number.person == person:
            phone_number.person = None

    @classmethod
    @orm.db_session
    def _sync_contact_phone_into_persons(cls):
        person_ids = orm.select(
            p.id for p in Person
            if p.contactPhone and p.contactPhone not in p.phoneNumbers
        )[:]
        if not person_ids:
            return
        LogAPI().Warning(
            f'Syncing preferred phone numbers onto {len(person_ids)} persons'
        )

        def sync(person):
            if person.contactPhone and person.contactPhone not in person.phoneNumbers:
                person.phoneNumbers.add(person.contactPhone)

        isolated_chunk_executer(
            person_ids,
            Person,
            sync,
            action_name='Sync preferred phone numbers into person list'
        )

    @classmethod
    @orm.db_session
    def _unlink_orphaned_persons(cls):
        person_ids = orm.select(
            p.id for p in Person
            if p.is_orphaned and (orm.count(p.phoneNumbers) > 0 or orm.count(p.old_phone_numbers) > 0)
        )[:]
        if not person_ids:
            return
        LogAPI().Warning(
            f'Unlinking phone numbers from {len(person_ids)} orphaned persons'
        )

        def unlink(person):
            phones_by_id = {
                phone.id: phone
                for phone in list(person.phoneNumbers) + list(person.old_phone_numbers)
            }
            for phone in phones_by_id.values():
                cls.unlink_person(phone, person)

        isolated_chunk_executer(
            person_ids,
            Person,
            unlink,
            action_name='Unlink phone numbers from orphaned persons'
        )

    @classmethod
    @orm.db_session
    def _clear_stale_legacy_person_links(cls):
        phone_ids = orm.select(
            n.id for n in PhoneNumbers
            if n.person is not None and n.person not in n.persons
        )[:]
        if not phone_ids:
            return
        LogAPI().Warning(
            f'Clearing leftover person mappings on {len(phone_ids)} phone numbers'
        )

        def clear_link(phone):
            if phone.person and phone.person not in phone.persons:
                phone.person = None

        isolated_chunk_executer(
            phone_ids,
            PhoneNumbers,
            clear_link,
            action_name='Clear leftover phone number person mappings'
        )
