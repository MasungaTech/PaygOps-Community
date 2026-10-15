from core_system.operational_entities.services.edit_client_group_service import EditClientGroupService
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual
from core_system.operational_entities.models import ClientGroup
from core_system.operational_entities.services.client_group_getter_service import ClientGroupGetterService
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll


class AllClientGroupResource(BaseAPIResourceAll):

    LIST_SERVICE = ClientGroupGetterService
    LIST_PERMISSION = ['ViewClients', 'ViewLeads']
    ADD_SERVICE = EditClientGroupService
    ADD_PERMISSION = ['AddClientGroups']

    MODEL = ClientGroup
    TAG = 'Locations'


class IndividualClientGroupResource(BaseAPIResourceIndividual):

    GET_SERVICE = ClientGroupGetterService
    # You should be able to view client groups if you can view clients the same way you can view villages
    GET_GLOBAL_PERMISSION = ['ViewClients', 'ViewLeads']
    EDIT_SERVICE = EditClientGroupService
    EDIT_PERMISSION = "EditClientGroups"
    DELETE_SERVICE = EditClientGroupService
    DELETE_PERMISSION = "DeleteClientGroups"
    OBJECT_NAME = 'ClientGroup'

    MODEL = ClientGroup
    TAG = 'Locations'