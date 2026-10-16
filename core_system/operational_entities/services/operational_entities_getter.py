from pony.orm.core import select

from constants import MAX_ENTITY_LEVEL
from core_system.operational_entities.models import (ClientGroup,
                                                     OperationalEntity, db)
from core_system.operational_entities.services.operational_entities_helper import \
    OperationalEntitiesHelper
from shared.logger.loggers import Error
from shared.services.base_getter_service import BaseGetterService
from shared.services.settings_service import SettingsService


class OperationalEntitiesGetterService(BaseGetterService):

    OBJ_NAME = 'Operational Entity'

    @classmethod
    def preprocess_list_filters(cls, user, **kwargs):
        if kwargs['parent']:
            parent = OperationalEntity.get(id=kwargs['parent'])
            if not parent:
                raise Error('OperationalEntity with id '+kwargs['parent'])
            kwargs['parent'] = parent
        return kwargs

    @classmethod
    def get_filtered_objects(cls, current_user, level=None, level_name=None,
        parent=None, managed_by=None, only_hierarchical=False,
        extra_permission=None, for_sync=False, stock_enabled=None, **kwargs):
        if level is not None:
            try:
                level = int(level)
            except ValueError:
                raise Error('level must be an integer')
        keys = OperationalEntitiesHelper.ENTITY_LEVELS_MAPPING.keys()
        if level and not OperationalEntitiesHelper.level_valid(level):
            raise Error('Wrong value \''+str(level)+'\' for level, must be one of '+str(keys))
        if level_name and not OperationalEntitiesHelper.level_name_valid(level_name):
            raise Error('level name must be one of '+str(keys))
        roles_in_entities = current_user.get_roles_in_entities_for_permission(
            extra_permission
        ) if extra_permission else current_user.roles_in_entities
        if for_sync:
            roles_in_entities = roles_in_entities.filter(lambda rie: rie.sync_entity)
        entities = OperationalEntity.select() if roles_in_entities.filter(
            entity=None
        ).exists() else cls.all_descendents_from_entites(select(rie.entity for rie in roles_in_entities))
        if only_hierarchical:
            entities = entities.filter(lambda e: not isinstance(e, ClientGroup))
        if level is not None:
            entities = entities.filter(
                lambda e: isinstance(e, OperationalEntitiesHelper.get_level_class(level))
            )
        elif level_name:
            entities = entities.filter(
                lambda e: isinstance(e, OperationalEntitiesHelper.get_level_name_class(level_name))
            )
        if parent:
            entities = entities.filter(lambda e: e.parent == parent)
        if managed_by:
            entities = entities.filter(lambda e: e in cls.managed_by(managed_by))
        if stock_enabled is not None:
            entities =  cls.stock_enabled_filter(entities, stock_enabled)
        return entities

    @classmethod
    def stock_enabled_filter(cls, entities, enabled=None):
        config = SettingsService.get_setting('OperationalEntitiesInventory')
        if not config:
            config = [True, True, True, False, False]
        levels = [i for i in range(len(config)) if config[i] is enabled]
        return entities.filter(lambda e: e.level in levels)

    @classmethod
    def managed_by(cls, user, level=None):
        entities = user.managed_operational_entities.select()
        current_level = MAX_ENTITY_LEVEL
        dest_level = min(0, level or 0, current_level)
        while current_level != dest_level:
            current_level -= 1
            entities = select(oe for oe in OperationalEntity if (
                oe in entities or oe.parent in entities
            ) and (not oe.user_in_charge or oe.user_in_charge == user))
        return entities.filter(level=level) if level else entities

    @classmethod
    def all_descendents_from_entites(cls, entities):
        return OperationalEntity.select(lambda o: o.ascendants.filter(lambda e: e in entities))

    @classmethod
    def get_list_for_mobile(cls, current_user, cached_ids):
        villages = OperationalEntitiesGetterService.get_list(current_user=current_user, only_hierarchical=True, for_sync=True)
        leads_and_client_persons_ids = cached_ids.get('lead_persons', []) + cached_ids.get('client_persons', [])
        client_and_leads_villages_ids = select(p.village.id for p in db.Person if p.id in leads_and_client_persons_ids)[:]
        return OperationalEntity.select(lambda v: v in villages or v.id in client_and_leads_villages_ids)
