from core_system.users.models.user_model import User
from sales_system.lead_generator.model import LeadGeneratorType
from shared.logger.loggers import Error
from shared.services.base_getter_service import BaseGetterService
from datetime import datetime


class LeadGeneratorTypeService(BaseGetterService):

    OBJ_NAME = 'Lead Generator Type'

    @classmethod
    def _add_from_data_and_user(cls, data, user):
        name = data.get('name')
        if LeadGeneratorType.get(name=name):
            raise Error('A Lead Generator Type with that name already exists')
        lg_type = LeadGeneratorType(name=name)
        return lg_type
    
    @classmethod
    def _edit_from_data_and_user(cls, lg_type, data, user):
        name = data.get('name')
        existing_type = LeadGeneratorType.get(name=name)
        if existing_type and existing_type != lg_type:
            raise Error('Another Lead Generator Type with that name already exists')
        if name != lg_type.name:
            lg_type.name = name
            for lg in lg_type.generators:
                lg.modifiedDate = datetime.now()
        return lg_type
    
    @classmethod
    def _delete_from_object_and_user(cls, lg_type, user):
        if lg_type.generators.count() > 0:
            raise Error('You cannot delete a lead generator type if there are generators with this type')
        else:
            lg_type.delete()

    @classmethod
    def get_filtered_objects(cls, current_user, name=None, exclude_default=False, **kwargs):
        lg_types = LeadGeneratorType.select()
        if exclude_default:
            lg_types = lg_types.filter(lambda lgt: lgt.name != 'Default Lead Generator')
        if name:
            # This must be exact equivalence for the get from name to work
            lg_types = lg_types.filter(lambda lgt: lgt.name == name)
        return lg_types
    