from tests.support.mock_query import MockQuery


class NullPerson:

    user = None
    client = None
    full_name = ' - '
    lead = MockQuery([])

    @property
    def phoneNumbers(self):
        return self

    def remove(self, phone_number):
        pass
