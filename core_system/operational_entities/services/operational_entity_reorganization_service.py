from core_system.operational_entities.services.operational_entities_helper import OperationalEntitiesHelper
from shared.logger.loggers import Error
from core_system.operational_entities.models import OperationalEntity, Region
from shared.services.settings_service import SettingsService


class OperationalEntityReorganizerService:

    @classmethod
    def get_entity_data(cls, entity, limit=None):
        oe = entity.children.select()
        if limit:
            oe = oe.limit(limit)
        return {
            'name': entity.name,
            'children': [cls.get_entity_data(c, limit=limit) for c in oe]
        }
    
    @classmethod
    def get_current_structure(cls, limit=3):
        oe = OperationalEntity.select(lambda oe: oe.level == OperationalEntitiesHelper.get_max_level_enabled())
        if limit:
            oe = oe.limit(limit)
        return [cls.get_entity_data(entity, limit=limit) for entity in oe]

    @classmethod
    def move_up_entities(cls, level_to_stop):
        entities_config = SettingsService.get_setting('OperationalEntities')
        if Region.select().count() > 1:
            raise Error('Moving up entities is not possible when there are more than one '+entities_config[4]['name'])
        region = Region.select().first()
        for zone in region.children:
            cls._create_upper_entity(
                zone, None, level_to_stop, force_user_in_charge=region.user_in_charge.id
            )
        region.delete()
        entities_config[OperationalEntitiesHelper.get_max_level_enabled()+1]['enabled'] = True
        SettingsService.set_setting('OperationalEntities', entities_config)

    @classmethod
    def _create_upper_entity(cls, entity, parent, level_to_stop, force_user_in_charge=None):
        data = entity.to_dict()
        data.update({
            'parent': parent,
        })
        del data['id']
        del data['mobile_uuid']
        del data['level']
        if force_user_in_charge and not data['user_in_charge']:
            data['user_in_charge'] = force_user_in_charge
        class_to_use = OperationalEntitiesHelper.get_level_class(entity.level+1)
        new_entity = class_to_use(**data)
        # Transfer one to many relationships
        new_entity.users_with_roles = entity.users_with_roles
        new_entity.notifications = entity.notifications
        new_entity.destined_stock = entity.destined_stock
        new_entity.reference_of_users = entity.reference_of_users
        new_entity.offers = entity.offers
        new_entity.addon_offers_allowed_for_leads = entity.addon_offers_allowed_for_leads
        new_entity.addon_offers_allowed_for_contracts = entity.addon_offers_allowed_for_contracts
        new_entity.quantity_stock_locations = entity.quantity_stock_locations

        if entity.level == level_to_stop:
            entity.parent = new_entity
        else:
            for sub_entity in entity.children:
                cls._create_upper_entity(sub_entity, new_entity, level_to_stop)
            entity.delete()

    @classmethod
    def preview(cls, level_to_stop):
        result = cls.get_current_structure()
        level = OperationalEntitiesHelper.get_max_level_enabled()
        return cls.create_preview_children(result, level, level_to_stop)

    @classmethod
    def create_preview_children(cls, children, level, level_to_stop):
        for child in children:
            if level == level_to_stop:
                child['children'] = [child.copy()]
            else:
                child['children'] = cls.create_preview_children(child['children'], level-1, level_to_stop)
        return children