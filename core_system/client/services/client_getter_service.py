from core_system.client.models import Client
from core_system.core_entities import db
from core_system.operational_entities.services.client_group_getter_service import \
    ClientGroupGetterService
from core_system.operational_entities.services.operational_entities_getter import \
    OperationalEntitiesGetterService
from payg_loan_system.devices.device_api.device_getter_service import \
    DeviceGetterService
from pony.orm import select
from shared.services.base_getter_service import BaseGetterService
from shared.services.settings_service import SettingsService
from shared.helpers.db_helpers import searchable_text


class   ClientGetterService(BaseGetterService):

    OBJ_NAME = 'Client'

    @classmethod
    def preprocess_list_filters(cls, user, **kwargs):
        kwargs['client_group'] = ClientGroupGetterService.extract_from_user_and_id(user, kwargs, 'client_group_id')
        kwargs['entity'] = OperationalEntitiesGetterService.extract_from_user_and_id(user, kwargs, 'entity_id')
        return kwargs

    @classmethod
    def get_from_filtered_view(cls, user, view=None, entity=None, portfolio=None, status=None, search=None, client_group=None, active=None, id=None):

        extra = {}
        if view == 'managed_by_me':
            extra = dict(managed_by=user)
        elif view == 'generated_by_me':
            extra = dict(generated_by=user)

        clients = cls.get_list(user, search=search, entity=entity, portfolio=portfolio, client_group=client_group, active=active, id=id, **extra)

        if status is not None:
            clients = cls.filter_by_status(clients, status)

        return clients

    @classmethod
    def filter_by_status(cls, clients, status):
        # return all clients marked as terminated.
        if status == 'terminated':
            return clients.filter(lambda c: c.termination_date is not None)
        # return all clients who have at least one active contract
        elif status == 'active_contracts':
            active_clients = db.Client.select(lambda c: c.active_contracts.count() > 0)
            return clients.filter(lambda c: c in active_clients)
        # return all clients who have at least one defaulted contract
        elif status == 'defaulted_contracts':
            return clients.filter(lambda c: c.defaulted_contracts.count() > 0)
        # return all clients who have at least one defaulted but not repossessed contract
        elif status == 'defaulted_not_repossessed_contracts':
            return clients.filter(lambda c: c.defaulted_contracts_with_device.count() > 0)
        # return all clients who have at least one cancelled contract
        elif status == 'cancelled_contracts':
            return clients.filter(lambda c: c.cancelled_contracts.count() > 0)
        # return all clients who have at least one completed contract
        elif status == 'completed_contracts':
            return clients.filter(lambda c: c.completed_contracts.count() > 0)
        # return all clients who have at least one overpaid contract
        elif status == 'overpaid_contracts':
            return clients.filter(lambda c: c.overpaid_contracts.count() > 0)
        # return all clients who have at least one completed or active contract
        elif status == 'active_completed_contracts':
            return clients.filter(lambda c: c.completed_contracts.count() + c.active_contracts.count() > 0)
        elif status == 'active_late_completed_contracts':
            return clients.filter(lambda c: c.completed_contracts.count() + c.active_contracts.count() + c.late_contracts.count() > 0)
        elif status == 'active_late_contracts':
            return clients.filter(lambda c: c.active_or_late_contracts.count() > 0)
        # return all clients who have at least one paused contract
        elif status == 'paused_contracts':
            return clients.filter(lambda c: c.paused_contracts.count() > 0)
        elif status == 'late_contracts':
            return clients.filter(lambda c: c.late_contracts.count() > 0)
        return clients

    @classmethod
    def get_clients_with_permission(cls, current_user, permission, for_sync=False, extra_permission=None, managed_by=None):
        clients = db.Client.select()
        if for_sync or managed_by or not current_user.can_access_in_all(permission) or (extra_permission and not current_user.can_access_in_all(extra_permission)):
            villages_ids, client_groups_ids = current_user.get_villages_and_client_groups_with_permission(permission, for_sync=for_sync, return_villages_ids=True, managed_by=managed_by)
            if extra_permission:
                villages_ids, client_groups_ids = set(villages_ids), set(client_groups_ids)
                if not isinstance(extra_permission, list):
                    extra_permission = [extra_permission]
                for p in extra_permission:
                    extra_villages_ids, extra_client_groups_ids = current_user.get_villages_and_client_groups_with_permission(p, for_sync=for_sync, return_villages_ids=True, managed_by=managed_by)
                    villages_ids = villages_ids.intersection(set(extra_villages_ids))
                    client_groups_ids = client_groups_ids.intersection(set(extra_client_groups_ids))
                villages_ids, client_groups_ids = list(villages_ids), list(client_groups_ids)
            if client_groups_ids:
                clients = clients.filter(lambda c: c.person.village.id in villages_ids or c.person.client_group.id in client_groups_ids)
            else:
                clients = clients.filter(lambda c: c.person.village.id in villages_ids)
        return clients

    @classmethod
    def get_filtered_objects(cls, current_user, entity=None, active=False, for_new_contract=False,
        managed_by=None, generated_by=None, created_by=None, portfolio=None, search=None, contract_reference=None,
        phone_number=None, serial_number=None, exact_serial_number=None, id=None, client_group=None, extra_permission=None, for_sync=False, custom_id=None, **kwargs):
        current_user = current_user.reload()
        clients = cls.get_clients_with_permission(current_user, 'ViewClients', for_sync=for_sync, extra_permission=extra_permission, managed_by=managed_by)
        if entity:
            clients = clients.filter(lambda c: c.person.village in entity.descendants)
        if active:
            clients = clients.filter(lambda c: c.active)
        if generated_by:
            clients = clients.filter(lambda c: generated_by.person.leadGenerator in select(l.generator for l in c.person.lead))
        if created_by:
            clients = clients.filter(lambda c: created_by in select(l.reporter for l in c.person.lead))
        if client_group:
            clients = clients.filter(lambda c: c.person.client_group == client_group)
        if portfolio:
            clients = clients.filter(lambda c: c in select(c.client for c in db.Contract if c.portfolio == portfolio))
        if search:
            from core_system.phone_numbers.services.phone_number_getter import \
                PhoneNumberGetterService
            persons = PhoneNumberGetterService.find_persons_if_search_is_number(search)
            if search.isdigit():
                search_int = int(search)
                exact_clients_ids = select(e.id for e in clients if e.id == search_int or e.person.custom_id == search or e.person in persons)[:]
            else:
                exact_clients_ids = select(e.id for e in clients if e.person.custom_id == search or e.person in persons)[:]
            search = searchable_text(search)
            search_clients_ids = select(e.id for e in clients if search in e.person.searchable_name)
            clients = Client.select(lambda e: e.id in exact_clients_ids+search_clients_ids)
        if id:
            clients = clients.filter(lambda c: c.id == id)
        if contract_reference:
            contract_clients = select(c.client for c in db.Contract.select(lambda c: contract_reference.lower() in c.reference.lower()))
            clients = clients.filter(lambda c: c in contract_clients)
        if phone_number:
            from core_system.phone_numbers.services.phone_number_getter import \
                PhoneNumberGetterService
            persons = PhoneNumberGetterService.find_persons_if_search_is_number(phone_number)
            clients = clients.filter(lambda c: c.person in persons)
        if serial_number:
            serial_clients = select(p.contract.client for p in DeviceGetterService.get_list(current_user, serial_number=serial_number))
            clients = clients.filter(lambda c: c in serial_clients)
        
        if exact_serial_number:
            serial_clients = select(p.contract.client for p in DeviceGetterService.get_list(current_user, exact_serial_number=exact_serial_number))
            clients = clients.filter(lambda c: c in serial_clients)
        if custom_id:
            clients = clients.filter(lambda c: c.person.custom_id == custom_id)
        if for_new_contract and not SettingsService.get_setting("AllowMultipleContracts"):
            clients = clients.filter(lambda c: c.eligible_for_new_contract)
        return clients

    @classmethod
    def get_clients_in_user_shop(cls, user, active=True):
        return cls.get_list(user, entity=user.shop, active=active)

    @staticmethod
    def active_filter(clients, active):
        return clients.filter(lambda c: c.active or c.person.lead.filter(lambda l: l.active)) if active else clients
    
    @classmethod
    def get_list_for_mobile(cls, user, cached_ids=None, **kwargs):
        clients_generated = []
        clients_created = []
        clients = cls.get_list(user, extra_permission=['SyncClientsMobile'], for_sync=True)
        clients_ids = list(select(c.id for c in clients if c.active))
        completed_clients = cls.get_list(user, extra_permission=['SyncCompletedClientsMobile'], for_sync=True)
        clients_ids += list(select(c.id for c in completed_clients if not c.active))
        if user.can_access('SyncAllCreatedClientsMobile'):
            clients_created = ClientGetterService.get_list(user, created_by=user)
            clients_ids += list(select(c.id for c in clients_created))
        if user.can_access('SyncAllGeneratedClientsMobile'):
            clients_generated = ClientGetterService.get_list(user, generated_by=user)
            clients_ids += list(select(c.id for c in clients_generated))
        clients = select(c for c in db.Client if c.id in clients_ids)
        return clients
