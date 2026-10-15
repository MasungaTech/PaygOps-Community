from constants import MAX_ENTITY_LEVEL
from core_system.operational_entities.services.edit_operational_entity_service import EditOperationalEntityService
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual
from core_system.operational_entities.models import HierarchicalOperationalEntity


class AllOperationalEntitiesResource(BaseAPIResourceAll):

    LIST_SERVICE = OperationalEntitiesGetterService
    ADD_SERVICE = EditOperationalEntityService
    LIST_PERMISSION = None
    ADD_PERMISSION = ['AddVillages', 'AddClusters', 'AddHubs', 'AddZones', 'AddRegions']
    FILTERS = {"only_hierarchical": True}
    ENTITY_REQUIRED = False


    EXTRA_LIST_PARAMS = {
        'level': {
            'in': 'query',
            'name': 'level',
            'schema': {
                'type': 'string',
                'format': "[0-"+str(MAX_ENTITY_LEVEL)+"]",
                "min": 0
            },
            "example": 0,
            'allowEmptyValue': True,
            'description': 'Allows for filtering entities by level'
        },
        'parent': {
            'in': 'query',
            'name': 'parent',
            'schema': {
                'type': 'string',
                'format': "[0-9]+"
            },
            "example": 12,
            'allowEmptyValue': True,
            'description': 'Allows for filtering entities by parent\'s id'
        },
    }

    MODEL = HierarchicalOperationalEntity
    TAG = 'Locations'


class IndividualOperationalEntityResource(BaseAPIResourceIndividual):

    GET_SERVICE = OperationalEntitiesGetterService
    EDIT_SERVICE = EditOperationalEntityService
    DELETE_SERVICE = EditOperationalEntityService
    DELETE_PERMISSION = None
    OBJECT_NAME = 'Operational Entity'

    GET_PERMISSION = None
    EDIT_PERMISSION = ['EditVillages', 'EditClusters', 'EditHubs', 'EditZones']
    EDIT_GLOBAL_PERMISSION = ['EditRegions']

    MODEL = HierarchicalOperationalEntity
    TAG = 'Locations'

    ALLOWED_API_CALLER = ["post"]

    @classmethod
    def _get_relevant_entity(cls, this_object):
        return this_object.parent
