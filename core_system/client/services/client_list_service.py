from core_system.client.services.client_tag_getter import ClientTagService
from pony import orm
from core_system.core_entities import db
from core_system.client.services.client_getter_service import ClientGetterService
from tests.support.mock_query import MockQuery


class ClientListService:
    
    @classmethod
    def filter_by_tags(cls, clients, tags):
        if not tags:
            return clients
        none_tags = clients
        for tag in tags:
            none_tags = none_tags.filter(lambda c: tag not in c.tags)
        return clients.filter(lambda c: c not in none_tags)

    @classmethod
    def filter_for_user(cls, filters, user):

        locations = filters.get('Location', [])
        statuses = filters.get('Status', [])
        tags = filters.get('Tags', [])
        offer_types = filters.get('OfferType', [])
        intl = lambda l: [int(i) for i in l]

        if not locations or not statuses:
            return MockQuery([])
        clients = ClientGetterService.get_list(user)
        if not 'all' in locations:
            clients = clients.filter(
                lambda client: client.person.village.parent.parent.id in intl(locations)
            )
        if not 'all' in statuses:

            none = clients.filter(lambda: False)

            active = ClientGetterService.filter_by_status(clients, 'active_contracts'
                                                        ) if 'active' in statuses else none

            defaulted = ClientGetterService.filter_by_status(clients, 'defaulted_contracts'
                                                           ) if 'defaulted' in statuses else none

            completed = ClientGetterService.filter_by_status(clients, 'completed_contracts'
                                                           ) if 'completed' in statuses else none
            
            late = ClientGetterService.filter_by_status(clients, 'late_contracts'
                                                           ) if 'late' in statuses else none

            clients = clients.filter(lambda c: c in active or c in defaulted or c in completed or c in late)
            
        if 'all' in tags:
            relevant_tags = ClientTagService.get_list(user)
            clients = ClientListService.filter_by_tags(clients, relevant_tags)
        elif not 'all' in tags:
            relevant_tags = ClientTagService.get_list(user).filter(lambda t: t.id in intl(tags))
            clients = ClientListService.filter_by_tags(clients, relevant_tags)
        if not 'all' in offer_types:
            clients_offer = orm.select(c.client for c in db.Contract if c.offer.type in offer_types)
            clients = clients.filter(lambda client: client in clients_offer)
        return clients
