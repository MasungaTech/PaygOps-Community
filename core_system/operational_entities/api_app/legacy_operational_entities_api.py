from core_system.operational_entities.services.legacy_operational_entities_services import (
    ClusterGetterService, EditClusterService, EditShopService, EditVillageService, ShopGetterService, VillageGetterService
) 
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual
from core_system.operational_entities.models import Cluster, Hub, Village

class AllShopsResource(BaseAPIResourceAll):

    LIST_SERVICE = ShopGetterService
    ADD_SERVICE = EditShopService
    LIST_PERMISSION = None
    ADD_PERMISSION = 'AddHubs'

    LIST_VARIABLE = 'not_empty_code'
    LIST_VARIABLE_TYPE = 'string'
    LIST_VARIABLE_FORMAT = 'integer'
    LIST_VARIABLE_EXAMPLES = ["1234", "1235", "1236"]
    VIEW_DOCS_PERMISSION = 'CreateAPITokenAdmin'

    MODEL = Hub
    TAG = 'Locations'
    DEPRECATED = ['get', 'post']


class IndividualShopResource(BaseAPIResourceIndividual):

    GET_SERVICE = ShopGetterService
    EDIT_SERVICE = EditShopService
    GET_PERMISSION = None
    EDIT_PERMISSION = 'EditHubs'
    OBJECT_NAME = 'Hub'
    ID_PARAM = {
        "name": "id",
        "property": "code", 
        "description": "The old id of the Entity (if it was created before the changes)",
        "required": True,
        "example": "12",
        "schema": {
            "type": "string"
        }
    }
    DEPRECATED = ['get', 'post', 'delete']
    VIEW_DOCS_PERMISSION = 'CreateAPITokenAdmin'

    MODEL = Hub
    TAG = 'Locations'


class AllClustersResource(BaseAPIResourceAll):

    LIST_SERVICE = ClusterGetterService
    ADD_SERVICE = EditClusterService
    LIST_PERMISSION = None
    ADD_PERMISSION = 'AddClusters'

    LIST_VARIABLE = 'not_empty_code'
    LIST_VARIABLE_TYPE = 'string'
    LIST_VARIABLE_FORMAT = 'integer'
    LIST_VARIABLE_EXAMPLES = ["1234", "1235", "1236"]

    MODEL = Cluster
    TAG = 'Locations'
    DEPRECATED = ['get', 'post']
    VIEW_DOCS_PERMISSION = 'CreateAPITokenAdmin'


class IndividualClusterResource(BaseAPIResourceIndividual):

    GET_SERVICE = ClusterGetterService
    EDIT_SERVICE = EditClusterService
    GET_PERMISSION = None
    EDIT_PERMISSION = 'EditClusters'
    OBJECT_NAME = 'Cluster'
    DEPRECATED = ['get', 'post', 'delete']
    VIEW_DOCS_PERMISSION = 'CreateAPITokenAdmin'


    ID_PARAM = {
        "name": "id",
        "property": "code", 
        "description": "The old id of the Entity (if it was created before the changes)",
        "required": True,
        "example": "12",
        "schema": {
            "type": "string"
        }
    }

    MODEL = Cluster
    TAG = 'Locations'

    @classmethod
    def _get_relevant_entity(cls, this_object):
        return this_object.parent


class AllVillagesResource(BaseAPIResourceAll):

    LIST_SERVICE = VillageGetterService
    DEPRECATED = ['get', 'post']
    ADD_SERVICE = EditVillageService
    LIST_PERMISSION = None
    ADD_PERMISSION = 'AddVillages'

    LIST_VARIABLE = 'not_empty_code'
    LIST_VARIABLE_TYPE = 'string'
    LIST_VARIABLE_FORMAT = 'integer'
    LIST_VARIABLE_EXAMPLES = ["1234", "1235", "1236"]
    VIEW_DOCS_PERMISSION = 'CreateAPITokenAdmin'

    MODEL = Village
    TAG = 'Locations'

class IndividualVillageResource(BaseAPIResourceIndividual):

    GET_SERVICE = VillageGetterService
    DEPRECATED = ['get', 'post', 'delete']
    VIEW_DOCS_PERMISSION = 'CreateAPITokenAdmin'
    EDIT_SERVICE = EditVillageService
    GET_PERMISSION = None
    EDIT_PERMISSION = 'EditVillages'
    OBJECT_NAME = 'Village'

    ID_PARAM = {
        "name": "id",
        "property": "code", 
        "description": "The old id of the Entity (if it was created before the changes)",
        "required": True,
        "example": "12",
        "schema": {
            "type": "string"
        }
    }

    MODEL = Village
    TAG = 'Locations'

    @classmethod
    def _get_relevant_entity(cls, this_object):
        return this_object.parent
