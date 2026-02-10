from shared.logger.loggers import Error
import json
from shared.api_helpers.hook_helpers.process_hook import add_hook_after_commit
from core_system.person.services.edit_person_service import EditPersonService
from core_system.portfolios.services.portfolio_getter_service import PortfolioGetterService
from core_system.client.models import ClientTag
from core_system.core_entities import db
from shared.services.base_service import BaseService


class ClientEditService(BaseService):

    @classmethod
    def validate_data(cls, client, data, user):
        if not user.can_access('EditClients', person=client.person):
            raise Error('INSUFFICIENT_PERMISSION', permission='EditClients')
        EditPersonService.validate_data(data)

    @classmethod
    def _edit_from_data_and_user(cls, client, client_data_dict, user):
        cls.validate_data(client, client_data_dict, user)
        EditPersonService.edit_person_from_data(client.person, client_data_dict, edit_phone_numbers=True, user=user)
        
        note = client_data_dict.get('note', None)
        if note is not None:
            client.Assets = note
        portfolio_id = client_data_dict.get('portfolio_id')
        if portfolio_id:
            portfolio = PortfolioGetterService.get_from_user_and_id(user, portfolio_id)
            (client.first_active_contract or client.last_contract).portfolio = portfolio

        # Tag processing, can be by ID or Name
        can_add_tags = user.can_access('AddTagsClients', person=client.person)
        tags = client_data_dict.get('tags')
        if tags and not can_add_tags:
            raise Error('INSUFFICIENT_PERMISSION', permission='AddTagsClients')
        if tags is not None:
            if not isinstance(tags, list):
                tags = tags.split(',')
            try:
                tags_id = [int(t) for t in tags]
                updated_tags = ClientTag.select().filter(lambda t: t.id in tags_id)
            except ValueError:
                updated_tags = ClientTag.select().filter(lambda t: t.name in tags)
            client.tags = updated_tags
            client.tag_added()

        # New API
        # Implicit tag creation is still supported for now but might be removed
        can_create_tags = user.can_access('CreateTagsClients', person=client.person)
        add_tags = client_data_dict.get('add_tags')
        if add_tags:
            for tag in add_tags:
                this_tag = ClientTag.get(name=tag)
                if not this_tag:
                    if not can_create_tags:
                        raise Error('INSUFFICIENT_PERMISSION', permission='CreateTagsClients')
                    client.tags.create(name=tag)
                else:
                    if not can_add_tags:
                        raise Error('INSUFFICIENT_PERMISSION', permission='AddTagsClients')
                    client.tags.add(this_tag)
            client.tag_added()

        remove_tags = client_data_dict.get('remove_tags')
        if remove_tags:
            for tag in remove_tags:
                this_tag = ClientTag.get(name=tag)
                if this_tag:
                    if not can_add_tags:
                        raise Error('INSUFFICIENT_PERMISSION', permission='AddTagsClients')
                    client.tags.remove(this_tag)
        
        add_hook_after_commit(db, 'client_edited', client.get_serialized_object())
        return client

    @classmethod
    def get_human_readable_error(cls, error):
        clean_error = EditPersonService.get_human_readable_error(error)
        return clean_error
