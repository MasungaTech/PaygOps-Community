from core_system.users.models.user_model import User
from pony import orm
from shared.services.base_getter_service import BaseGetterService
from shared.logger.loggers import LogAPI
from shared.helpers.db_helpers import searchable_text


class UserGetterService(BaseGetterService):

    OBJ_NAME = 'User'

    
    @classmethod
    def get_from_filtered_view(cls, user, view=None, entity=None, search=None, active=None, role=None, role_type=None):
        if view == 'reference_entity':
            entity = user.shop
        users = cls.get_list(user, search=search, entity=entity, active=active, role=role, role_type=role_type)
        return users

    @classmethod
    def get_filtered_objects(cls, current_user, search=None, active='all', entity=None, role=None, role_type=None, **kwargs):
        users = User.select()
        if not current_user.reload().can_access_in_all("ViewUsers"):
            entities_with_permissions = current_user.get_entities_with_permission('ViewUsers')
            if current_user.can_access('ViewOwnUsers'):
                users = users.filter(lambda u: u.shop in entities_with_permissions or (u == current_user))
            elif current_user.get_entities_with_permission('ViewUsers'):
                users = users.filter(lambda u: u.shop in entities_with_permissions)
            else:
                users = users.filter(lambda u: u.id==-1)
        if role_type:
            users = users.filter(lambda u: u.AuthorizationLevel.type == role_type)
        if role:
            users = users.filter(lambda u: u.AuthorizationLevel == role)
        if entity:
            users = users.filter(lambda u: u.shop in entity.descendants)
        if active != 'all':
            if active == 'default':
                active = 'active'
            users = users.filter(lambda u: u.active==(active=='active'))
        if search:
            from core_system.phone_numbers.services.phone_number_getter import \
                PhoneNumberGetterService
            persons = PhoneNumberGetterService.find_persons_if_search_is_number(search)
            if search.isdigit():
                search_int = int(search)
                exact_users_ids = orm.select(e.id for e in users if e.id == search_int or e.person in persons)[:]
            else:
                exact_users_ids = orm.select(e.id for e in users if e.person in persons)[:]
            search = searchable_text(search)
            search_users_ids = orm.select(e.id for e in users if search in e.person.searchable_name)
            all_matching_ids = exact_users_ids + search_users_ids
            users = users.filter(lambda e: e.id in all_matching_ids or search in e.username or search in e.email)
        return users

    @classmethod
    def get_by_username(cls, username):
        clean_username = username.replace(' ', '')
        users_matching = orm.select(user for user in User if user.username.lower() == clean_username.lower())
        # in case two users have the same username we raise a warning and return the first one
        if len(users_matching) > 1:
            LogAPI.Warning(f'More than one user with username [{username}]')
            return users_matching.order_by(orm.desc(User.id)).first()
        else:
            return users_matching.first() if users_matching else None
    
    @classmethod
    def get_by_email(cls, email):
        clean_email = email.replace(' ', '').lower()
        return User.select(lambda u: u.email.lower() == clean_email).first()
