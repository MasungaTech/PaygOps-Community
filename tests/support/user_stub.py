from tests.support.mock_query import MockQuery
from pony import orm
from mock import Mock
from core_system.core_entities import db
from survey_system.models.survey_answer import SurveyAnswer
from core_system.role.methods.getters import (get_role_from_name, get_authorized_pages_from_role_id)


class UserStub:

    cash_collection_limit = None
    managed_operational_entities = MockQuery([])

    @property
    def shop(self):
        return ModelStub()

    def is_expired(self):
        False
    
    def reload(self):
        return self

    def get_relevant_survey_answers_for_mobile(self, clientIds):
        return orm.select(village for village in SurveyAnswer if village.id == -1)
        #return NullQueryObject()

    def get_last_three_interactions_from_clients_mobile(self, clientIds):
        return []

    def get_discussed_topics_for_mobile(self, clientIds):
        return orm.select(village for village in db.DiscussedTopic if village.id == -1)

    def can_access(self, permission, entity=None, person=None, check_special=True):
        return permission in self.get_accessible_permissions()

    def get_accessible_permissions(self):
        return get_authorized_pages_from_role_id(self.AuthorizationLevel.id)

    @property
    def id(self):
        return 1

    @property
    def username(self):
        pass

    @property
    def AuthorizationLevel(self):
        return get_role_from_name('SuperAdmin')

    def get_cash_account(self):
        return Mock(get_balance=lambda: 0)


class NullQueryObject:
    def __iter__(self):
        return self

    def __next__(self):
        raise StopIteration()

    def without_distinct(self):
        return self

    def for_update(self):
        return []

    def filter(self, lb):
        return []


class ModelStub:
    def get_clusters(self):
        return [self]
