import factory
from functools import partial
from datetime import datetime
from sales_system.lead_generator.model import LeadGenerator
from mock import Mock
from tests.factories.factories import PersonFactory, UserFactory


class LeadGeneratorFactory(factory.Factory):
    class Meta:
        model = LeadGenerator
    id = factory.Sequence(lambda n: n)
    person = factory.SubFactory(PersonFactory)
    type = 'Sales Leader'
    # phoneNumber = '+999111222333'
    typicalCommission = 0
    working = 1

    @classmethod
    def stub(cls, *args, **kwargs):
        lead_generator = super().stub(*args, **kwargs)
        return lead_generator

    @classmethod
    def generate_user_with_lead_generator(cls, lead_generator=True):
        if lead_generator:
            lead_generator = LeadGeneratorFactory.stub()
        else:
            lead_generator = None
        person = PersonFactory.stub(leadGenerator=lead_generator)
        user = UserFactory.stub(person=person)
        return user
