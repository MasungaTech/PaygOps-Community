from random import randint

from pony import orm
from pony.orm.core import flush
import pytest

from core_system.person.models.person_model import Person, PersonType
from core_system.phone_numbers.model import PhoneNumbers
from core_system.phone_numbers.services.phone_number_cleanup_service import \
    PhoneNumberCleanupService
from core_system.phone_numbers.services.phone_number_getter import \
    PhoneNumberGetterService
from payg_loan_system.payments.models.wallet import PaymentWallet
from shared.helpers.client_creator import ClientCreator


def _unique_phone(prefix='+255'):
    for _ in range(20):
        number = prefix + str(randint(10**8, 10**9 - 1))
        if not PhoneNumbers.get(number=number):
            return number
    raise RuntimeError('Could not generate a unique phone number')


class TestPhoneNumberGetter:

    @orm.db_session
    def test_find_persons_ignores_unassigned_numbers(self):
        lead = ClientCreator.create_lead()
        assigned_number = lead.person.phoneNumbers.select().first().number
        search = assigned_number.replace('+', '')
        leftover = PhoneNumbers(number='+1' + search)
        flush()

        matches = PhoneNumberGetterService.find_phone_numbers(search)
        persons = PhoneNumberGetterService.find_persons_if_search_is_number(search)

        assert leftover not in matches
        assert matches.count() == 1
        assert lead.person in persons

    @orm.db_session
    def test_find_phone_numbers_returns_nothing_for_unassigned_number(self):
        leftover_number = _unique_phone('+254')
        leftover = PhoneNumbers(number=leftover_number)
        flush()

        matches = PhoneNumberGetterService.find_phone_numbers(leftover_number.replace('+', ''))

        assert leftover is not None
        assert matches.count() == 0

    @orm.db_session
    def test_search_still_finds_lead_after_legacy_person_link_is_cleared(self):
        lead = ClientCreator.create_lead()
        phone = lead.person.phoneNumbers.select().first()
        phone.person = None
        flush()

        assert lead.person in PhoneNumberGetterService.find_persons_if_search_is_number(phone.number)
        assert lead in PhoneNumberGetterService.get_leads_by_phone_number(phone.number)


class TestPhoneNumberCleanup:

    @orm.db_session
    def test_cleanup_keeps_unassigned_phone_number_rows(self):
        leftover_number = _unique_phone('+254')
        PhoneNumbers(number=leftover_number)
        flush()

        PhoneNumberCleanupService.cleanup_unassigned_phone_numbers()

        leftover = PhoneNumbers.get(number=leftover_number)
        assert leftover is not None
        assert leftover.persons.count() == 0
        assert PhoneNumberGetterService.find_phone_numbers(leftover_number.replace('+', '')).count() == 0

    @orm.db_session
    def test_cleanup_unlinks_orphaned_persons_without_deleting_the_number(self):
        leftover_number = _unique_phone('+255')
        phone = PhoneNumbers(number=leftover_number)
        orphaned = Person(name='TEST1', surname='TEST1', type=PersonType.unknown)
        phone.persons.add(orphaned)
        phone.person = orphaned
        flush()
        orphaned_id = orphaned.id

        PhoneNumberCleanupService.cleanup_unassigned_phone_numbers()

        leftover = PhoneNumbers.get(number=leftover_number)
        assert leftover is not None
        assert leftover.persons.count() == 0
        assert leftover.person is None
        leftover_person = Person.get(id=orphaned_id)
        if leftover_person:
            assert leftover_person.phoneNumbers.count() == 0
        assert PhoneNumberGetterService.find_phone_numbers(leftover_number.replace('+', '')).count() == 0

    @orm.db_session
    def test_cleanup_clears_leftover_person_mapping_without_deleting_the_number(self):
        lead = ClientCreator.create_lead()
        leftover_number = _unique_phone('+234')
        PhoneNumbers(number=leftover_number, person=lead.person)
        flush()

        PhoneNumberCleanupService.cleanup_unassigned_phone_numbers()

        leftover = PhoneNumbers.get(number=leftover_number)
        assert leftover is not None
        assert leftover.person is None
        assert lead.person not in leftover.persons
        assert leftover not in PhoneNumberGetterService.find_phone_numbers(leftover_number.replace('+', ''))

    @orm.db_session
    def test_cleanup_does_not_remove_wallet_links(self):
        wallet = PaymentWallet.select().first()
        if not wallet:
            pytest.skip('No payment wallet in test DB')
        leftover_number = _unique_phone('+254')
        leftover = PhoneNumbers(number=leftover_number, payment_wallet=wallet)
        flush()

        PhoneNumberCleanupService.cleanup_unassigned_phone_numbers()

        kept = PhoneNumbers.get(number=leftover_number)
        assert kept is not None
        assert kept.payment_wallet == wallet
