from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from core_system.person.services.edit_person_service import EditPersonService
from sales_system.lead_generator.services.lead_generator_type_service import LeadGeneratorTypeService
from sales_system.lead_generator.model import LeadGenerator
from core_system.person.models.person_model import PersonType
from core_system.users.services.user_getter_service import UserGetterService
from shared.logger.loggers import Error
import config
from shared.services.base_service import BaseService


class LeadGeneratorEditService(BaseService):

    @classmethod
    def _add_from_data_and_user(cls, data, user):
        user_to_merge = cls._get_user_to_merge_from_data(data, user)
        if user_to_merge:
            if cls._user_has_lead_generator(user_to_merge):
                raise Error('USER_HAS_LEAD_GENERATOR')
            person = user_to_merge.person
        else:
            data['person_type'] = PersonType.leadGenerator
            person = EditPersonService.add_from_data_and_user(data, user, is_user=True)        
        lg_type = LeadGeneratorTypeService.get_from_user_and_properties(user, name=data['type'], strict=True)
        lg = LeadGenerator(person=person, type=lg_type)
        cls._edit_additional_data(lg, data, user)
        return lg

    @classmethod
    def _edit_from_data_and_user(cls, lg, data, user):
        if lg.type.name == 'Default Lead Generator':
            raise Error('Not possible to edit Default Lead Generators')
        user_to_merge = cls._get_user_to_merge_from_data(data, user)
        if user_to_merge:
            cls.merge_with_user(lg, user_to_merge)
        EditPersonService.edit_person_from_data(lg.person, data, edit_phone_numbers=True, user=user, is_user=True)
        cls._edit_additional_data(lg, data, user)

    @classmethod
    def _edit_additional_data(cls, lg, data, user):
        if data.get('type'):
            lg.type = LeadGeneratorTypeService.get_from_user_and_properties(user, name=data.get('type'), strict=True)
        lg.working = cls._to_bool(data.get('working', lg.working))
        #lg.start_date = data.get('start_date', lg.start_date) # We purposedly dont allow to edit the start date

    @classmethod
    def _get_user_to_merge_from_data(cls, data, acting_user):
        merge_from_user_id = data.get('linked_user_id')
        if merge_from_user_id:
            user = UserGetterService.get_from_user_and_id(acting_user, merge_from_user_id, strict=True)
            return user
        return None

    @classmethod
    def validate_data(cls, data, user):
        EditPersonService.validate_data(data)
        if 'type' in data:
            lead_generator_type = data.get('type')
            if not lead_generator_type:
                raise Error('Lead generator type is required')
            if not LeadGeneratorTypeService.get_from_user_and_properties(user, name=lead_generator_type):
                raise Error(f'Invalid Lead generator type {lead_generator_type}')
        if 'linked_user_id' in data:
            if not str(data['linked_user_id']).isdigit():
                raise Error('User Id is not a valid number')
            user = UserGetterService.get_from_user_and_id(user, data['linked_user_id'], strict=True)
            if user.person.leadGenerator:
                raise Error('The user already has a Lead Generator associated')


    @classmethod
    def merge_with_user(cls, lead_generator, user):
        if cls._user_has_lead_generator(user):
            raise Error('The user you are trying to merge already has a lead generator associated. ', code='USER_HAS_LEAD_GENERATOR')
        if cls._lead_generator_has_user(lead_generator):
            raise Error('The lead generator you are trying to merge already has a user associated. ', code='LEAD_GENERATOR_HAS_USER')
        user.person.leadGenerator = lead_generator
        # We remove the old person. Checking if it has other things associated with it. (optional)

    @classmethod
    def _user_has_lead_generator(cls, user):
        return user.person.leadGenerator is not None

    @classmethod
    def _lead_generator_has_user(cls, lead_generator):
        return lead_generator.person.user is not None

    @staticmethod
    def _to_bool(x):
        return x not in [False, 0, '', 'False', 'off', '0', None]

    @classmethod
    def get_affected_entity(cls, data, user, **kwargs):
        user_to_merge = cls._get_user_to_merge_from_data(data, user)
        if user_to_merge:
            return user_to_merge.shop
        if 'village' in data:
            return OperationalEntitiesGetterService.extract_from_user_and_id(user, data, 'village', strict=False)
        if 'l0_entity_id' in data:
            return OperationalEntitiesGetterService.extract_from_user_and_id(user, data, 'l0_entity_id', strict=False)
        return None
