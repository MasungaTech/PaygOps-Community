from pony import orm
from core_system.operational_entities.models import OperationalEntity


class OperationalEntitySetService:
    
    @classmethod
    def get_intersection_of_entities_sets(cls, entites1, entities2):
        return entites1.filter(lambda o: o.ascendants.filter(lambda e: e in entities2).count() > 0)

