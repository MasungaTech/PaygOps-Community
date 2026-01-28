from flask_restful import Resource, request
from pony.orm import db_session
from core_system.client.services.client_getter_service import ClientGetterService
from core_system.users.services.current_user_service import get_current_api_user
from core_system.users.services.user_getter_service import UserGetterService
from sales_system.lead_generator.services.lead_generator_getter_service import LeadGeneratorGetterService
from shared.api_helpers.server_helpers.jwt_and_schema_verification import verify
from core_system.phone_numbers.services.phone_number_finder import PhoneNumberFinder
from core_system.client.models import Client
from core_system.users.models.user_model import User
from sales_system.lead_generator.model import LeadGenerator

phone_number_finder = PhoneNumberFinder


class PhoneNumberPreferredResource(Resource):

    @verify(permissions='ViewPhoneNumbers')
    @db_session
    def get(self):
        current_user = get_current_api_user()
        result = None

        client_id = request.args.get('client_id')
        user_id = request.args.get('user_id')
        user_in_charge_of_client_id = request.args.get('user_in_charge_of_client_id')
        lead_generator_id = request.args.get('lead_generator_id')

        if client_id:
            this_client = ClientGetterService.get_from_user_and_id(current_user, client_id, strict=True)
            result = phone_number_finder.find_person_preferred_number(this_client.person)

        elif user_id:
            this_user = UserGetterService.get_from_user_and_id(current_user, user_id, strict=True)
            result = phone_number_finder.find_person_preferred_number(this_user.person)

        elif user_in_charge_of_client_id:
            this_client = ClientGetterService.get_from_user_and_id(current_user, user_in_charge_of_client_id, strict=True)
            user_in_charge_of_client = this_client.get_user_in_charge()
            result = phone_number_finder.find_person_preferred_number(user_in_charge_of_client.person)

        elif lead_generator_id:
            this_lead_generator = LeadGeneratorGetterService.get_from_user_and_id(current_user, lead_generator_id, strict=True)
            result = phone_number_finder.find_person_preferred_number(this_lead_generator.person)

        return [{'phone_number': result}] if result else [], 200
