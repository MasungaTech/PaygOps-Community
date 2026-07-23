from pony import orm
from shared.logger.loggers import Error
from core_system.operational_entities.services.operational_entities_helper import OperationalEntitiesHelper



class OperationalEntityMerger:

    @classmethod
    def merge(cls, from_entity, to_entity):
        if not (from_entity and to_entity):
            raise Error('ENTITIES_MUST_EXIST')
        if from_entity.level != to_entity.level:
            raise Error('CANNOT_MERGE_ENTITY_OF_DIFFERENT_LEVELS')
        # We move common stuff
        for notification in from_entity.notifications:
            notification.operational_entity = to_entity.id
        for stock in from_entity.destined_stock:
            stock.destination_entity = to_entity.id
        for offer in from_entity.offers:
            to_entity.offers.add(offer)
        # We also merge users with roles
        users = orm.select(ur.user for ur in to_entity.users_with_roles)
        for user_with_role in from_entity.users_with_roles:
            if user_with_role.user not in users:
                to_entity.users_with_roles.create(
                    user=user_with_role.user,
                    role=user_with_role.role,
                    sync_entity=user_with_role.sync_entity
                )
        # We merge the users reference entity
        for user_with_ref in from_entity.reference_of_users:
            user_with_ref.shop = to_entity
        if from_entity.level == 0:
            cls._merge_village(from_entity, to_entity)
        else:
            cls._merge_entity(from_entity, to_entity)

    @classmethod
    def _merge_entity(cls, from_entity, to_entity):
        parent_level_name = OperationalEntitiesHelper.get_custom_level_name(from_entity.level).lower()
        child_level_name = OperationalEntitiesHelper.get_custom_level_name(from_entity.level-1).lower()
        to_entity_names = [e.name for e in to_entity.children]
        for child in from_entity.children:
            if child.name in to_entity_names:
                raise Error('CHILD_WITH_SAME_NAME_EXIST', child_entity_name=child.name, parent_level_name=parent_level_name, child_level_name=child_level_name)
            child.parent = to_entity
        orm.flush()
        from_entity.delete()

    @classmethod
    def _merge_village(cls, from_entity, to_entity):
        for person in from_entity.persons:
            person.village = to_entity.id
        for old_person in from_entity.old_persons:
            old_person.old_entity = to_entity.id
        for new_person in from_entity.new_persons:
            new_person.new_entity = to_entity.id
        orm.flush()
        from_entity.delete()