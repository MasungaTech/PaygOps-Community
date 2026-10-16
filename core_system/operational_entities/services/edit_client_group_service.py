from core_system.operational_entities.services.operational_entities_helper import OperationalEntitiesHelper
from shared.logger.loggers import Error
from core_system.users.services.user_getter_service import UserGetterService
from core_system.operational_entities.models import ClientGroup
from shared.services.settings_service import SettingsService
from shared.services.base_service import BaseService


class EditClientGroupService(BaseService):

    @classmethod
    def _add_from_data_and_user(cls, data, user, sync_entity=False):
        cls.validate_data(user, data, for_edit=False)
        user_in_charge_id = data.get('user_in_charge_id')
        user_in_charge = UserGetterService.get_from_user_and_id(user, user_in_charge_id, strict=True)
        name = data.get('name')
        client_group = ClientGroup(
            name=name,
            user_in_charge=user_in_charge,
            description=data.get('description') or '',
        )
        client_group.users_with_roles.create(user=user_in_charge, sync_entity=sync_entity or SettingsService.get_setting('SyncEntityByDefaultForNewUsersInCharge'))
        return client_group

    @classmethod
    def _edit_from_data_and_user(cls, group, data, user):
        cls.validate_data(user, data, for_edit=True)
        if 'name' in data:
            group.name =data['name']
        if 'user_in_charge_id' in data:
            user_in_charge_id = data['user_in_charge_id']
            user_in_charge = UserGetterService.get_from_user_and_id(user, user_in_charge_id, strict=True)
            if group.user_in_charge != user_in_charge and not group.users_with_roles.select(lambda uwr: uwr.user == user_in_charge).exists():
                group.users_with_roles.create(user=user_in_charge, sync_entity=SettingsService.get_setting('SyncEntityByDefaultForNewUsersInCharge'))
            group.user_in_charge = user_in_charge
        if 'description' in data:
            group.description=data.get('description')
        return group
    
    @classmethod
    def _delete_from_object_and_user(cls, group, user):
        if group.persons.count():
            raise Error('You cannot delete a client group with clients or leads on it')
        group.delete()

    @classmethod
    def validate_data(cls,user, data, for_edit=False):
        if for_edit:
            if not user.can_access('EditClientGroups'):
                raise Error('Not enough permission to edit client groups')
            if 'client_group_id' in data:
                client_group_id = data['client_group_id']
                if not client_group_id:
                    raise Error('client_group_id is required')
                group = ClientGroup.get(id=client_group_id)
                if not group:
                    raise Error('Client group does not exist')
        else:
            if not user.can_access('AddClientGroups'):
                raise Error('Not enough permission to add client groups') 
            if 'name' in data:
                name = data['name']
                if not name:
                    raise Error('name is required')
            if 'user_in_charge_id' in data:
                user_in_charge_id = data['user_in_charge_id']
                if not user_in_charge_id:
                    raise Error('user_in_charge_id is required')
