from tests.factories.factories import PersonFactory


class TestPerson:
    def test_has_lead_generator_returns_false(self):
        person = PersonFactory.stub()

        assert not person.leadGenerator

    def test_has_lead_generator_returns_true(self):
        person = PersonFactory.stub(leadGenerator=1)

        assert person.leadGenerator
