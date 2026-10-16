import data_system.client_stats as ClientStats
from payg_loan_system.contracts.services.contract_list_service import ContractListService
from datetime import datetime, timedelta


def bindClientStats(thisEntityWithClients):
    thisEntityWithClients.getClientsRegisteredInPeriodCount = clients_getClientsRegisteredInPeriodCount
    thisEntityWithClients.getActiveClientCount = clients_getActiveClientCount
    thisEntityWithClients.getInactiveClientCount = clients_getInactiveClientCount
    thisEntityWithClients.getDroppedClientCount = clients_getDroppedClientCount
    thisEntityWithClients.getCurrentClientCount = clients_getCurrentClientCount
    thisEntityWithClients.getClientsRegisteredInPeriodCount = clients_getClientsRegisteredInPeriodCount
    thisEntityWithClients.getClientsDroppedInPeriodCount = clients_getClientsDroppedInPeriodCount
    thisEntityWithClients.getActiveRecentClientCount = clients_getActiveRecentClientCount
    thisEntityWithClients.getInactiveRecentClientCount = clients_getInactiveRecentClientCount
    thisEntityWithClients.getDroppedRecentClientCount = clients_getDroppedRecentClientCount
    thisEntityWithClients.get_all_active_clients = get_all_active_clients
    thisEntityWithClients.get_PAR_data = clients_get_PAR_data
    thisEntityWithClients.get_contracts = get_contracts
    thisEntityWithClients.get_recent_contracts = get_recent_contracts
    thisEntityWithClients.getClientWithPausedContractsCount = clients_getClientWithPausedContractsCount


def get_contracts(self, active=True):
    contracts = ContractListService.get_from_clients(self.get_clients(active=active))
    return contracts


def get_recent_contracts(self, active=True):
    contracts = self.get_contracts(active=active)
    recent_date = datetime.now() - timedelta(days=90)
    return contracts.filter(lambda c: c.start_time >= recent_date)


def get_all_active_clients(self):
    return ClientStats.get_all_active_clients(self.get_clients())


def clients_getActiveClientCount(self):
    return ClientStats.getActiveClientCount(self.get_contracts())


def clients_getInactiveClientCount(self):
    return ClientStats.getInactiveClientCount(self.get_contracts())


def clients_getDroppedClientCount(self):
    return ClientStats.getDroppedClientCount(self.get_clients(active=False))


def clients_getCurrentClientCount(self):
    return ClientStats.getCurrentClientCount(self.get_clients(active=True))


def clients_get_PAR_data(self):
    return ClientStats.get_PAR_data(self.get_contracts(active=False))


def clients_getClientsRegisteredInPeriodCount(self, fromDate, toDate):
    return ClientStats.getClientsRegisteredInPeriodCount(self.get_clients(active=False), fromDate, toDate)


def clients_getClientsDroppedInPeriodCount(self, fromDate, toDate):
    return ClientStats.getClientsDroppedInPeriodCount(self.get_clients(active=False), fromDate, toDate)


def clients_getActiveRecentClientCount(self):
    return ClientStats.getActiveClientCount(self.get_recent_contracts())


def clients_getInactiveRecentClientCount(self):
    return ClientStats.getInactiveClientCount(self.get_recent_contracts())


def clients_getDroppedRecentClientCount(self):
    return ClientStats.getDroppedClientCount(ClientStats.getRecentlyRegisteredClients(self.get_clients(active=False)))

def clients_getClientWithPausedContractsCount(self):
    return ClientStats.getClientWithPausedContractsCount(self.get_clients(active=False))




