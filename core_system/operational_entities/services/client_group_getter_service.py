from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from shared.services.base_getter_service import BaseGetterService


class ClientGroupGetterService(BaseGetterService):

    OBJ_NAME = 'Client Group'

    @classmethod
    def get_filtered_objects(cls, current_user, **kwargs):
        return OperationalEntitiesGetterService.get_filtered_objects(current_user, level=-1, **kwargs)
    
    @classmethod
    def get_list_for_mobile(cls, current_user, cached_ids):
        return cls.get_list(current_user, for_sync=True)
