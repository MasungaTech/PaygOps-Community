from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual
from sales_system.lead_generator.services.lead_generator_type_service import LeadGeneratorTypeService
from sales_system.lead_generator.model import LeadGeneratorType


class AllLeadGeneratorTypeResource(BaseAPIResourceAll):
    LIST_SERVICE = LeadGeneratorTypeService
    ADD_SERVICE = LeadGeneratorTypeService
    LIST_PERMISSION = ['ViewLeadGenerators']
    ADD_PERMISSION = 'ConfigureSalesManagementAdmin'

    MODEL = LeadGeneratorType
    OBJECT_NAME = 'Lead Generator Type'
    TAG = 'Lead Generators'

    ENTITY_REQUIRED = False


class IndividualLeadGeneratorTypeResource(BaseAPIResourceIndividual):
    GET_SERVICE = LeadGeneratorTypeService
    EDIT_SERVICE = LeadGeneratorTypeService
    DELETE_SERVICE = LeadGeneratorTypeService
    GET_GLOBAL_PERMISSION = ['ViewLeadGenerators']
    EDIT_GLOBAL_PERMISSION = 'ConfigureSalesManagementAdmin'
    DELETE_GLOBAL_PERMISSION = 'ConfigureSalesManagementAdmin'

    MODEL = LeadGeneratorType
    OBJECT_NAME = 'Lead Generator Type'
    TAG = 'Lead Generators'
        