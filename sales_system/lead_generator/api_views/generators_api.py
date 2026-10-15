from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual
from sales_system.lead_generator.services.lead_generator_getter_service import LeadGeneratorGetterService
from sales_system.lead_generator.services.lead_generator_edit_service import LeadGeneratorEditService
from sales_system.lead_generator.services.lead_generator_commission_service import LeadGeneratorCommissionService
from sales_system.lead_generator.model import LeadGenerator
from flask_restful import Resource
from pony.orm import db_session
from shared.api_helpers.server_helpers.jwt_and_schema_verification import verify
from flask import request
from core_system.users.services.current_user_service import get_current_api_user


class AllLeadGeneratorResource(BaseAPIResourceAll):
    LIST_SERVICE = LeadGeneratorGetterService
    ADD_SERVICE = LeadGeneratorEditService
    LIST_PERMISSION = ['ViewLeadGenerators', 'ViewOwnLeadGenerators']
    ADD_PERMISSION = 'AddLeadGenerators'

    MODEL = LeadGenerator
    OBJECT_NAME = 'Lead Generator'
    TAG = 'Lead Generators'

    ENTITY_REQUIRED = False


class IndividualLeadGeneratorResource(BaseAPIResourceIndividual):
    GET_SERVICE = LeadGeneratorGetterService
    EDIT_SERVICE = LeadGeneratorEditService
    GET_GLOBAL_PERMISSION = ['ViewLeadGenerators', 'ViewOwnLeadGenerators']
    EDIT_GLOBAL_PERMISSION = 'EditLeadGenerators'
    
    MODEL = LeadGenerator
    OBJECT_NAME = 'Lead Generator'
    TAG = 'Lead Generators'

    @classmethod
    def _get_relevant_person(cls, this_object):
        return this_object.person


class LeadGeneratorCommissionResource(Resource):

    @verify(permissions=['EditLeads'])
    @db_session
    def post(self, id):
        data = request.json
        current_user = get_current_api_user()
        lead_generator = LeadGeneratorGetterService.get_from_user_and_id(current_user, id, strict=True, main_resource=True)
        lead_ids = [int(k.replace('"', '').replace("'", "")) for k,v in data.get("check_commission").items()] if data.get("check_commission") else []
        create_expenses = True if data.get('create_expense') in ['True', 'true', True] else False
        return LeadGeneratorCommissionService.process_commissions(lead_generator, current_user, lead_ids, create_expenses)

        