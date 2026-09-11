from core_system.client.services.client_getter_service import ClientGetterService
from payg_loan_system.contracts.models.contract_status import ContractStatus
from pony.orm import count, select

from datetime import datetime, timedelta
from decimal import Decimal

from payg_loan_system.contracts.services.contract_list_service import ContractListService
from payg_loan_system.contracts.services.contract_stats_service import ContractStatsService


def getCurrentClients(Clients):
    return Clients.filter(lambda C: C.contracts.select(lambda con: con.status == ContractStatus.active or con.status == ContractStatus.late).count() != 0)


def getCurrentClientCount(Clients):
    return getCurrentClients(Clients).count()


def get_all_active_clients(clients):
    return ClientGetterService.filter_by_status(clients, 'active_contracts')


def getDroppedClientCount(Clients):
    return Clients.filter(lambda C: C.defaulted_contracts.count() > 0).count()

def getClientWithPausedContractsCount(Clients):
    return Clients.filter(lambda C: C.contracts.select(lambda con: con.status == ContractStatus.paused).count() > 0).count()


def getClientCountInPeriod(Clients, fromDate, toDate):
    return Clients.filter(lambda C: C.RegistrationDate <= fromDate
                          and (not C.termination_date or C.termination_date > toDate))


def getInactiveClientCount(contracts):
    contracts = ContractListService.filter_by_payment_due_before(contracts, datetime.now())
    return contracts.count()


def getActiveClientCount(contracts):
    contracts = ContractListService.filter_only_active(contracts)
    return contracts.count() - getInactiveClientCount(contracts)


def get_PAR_data(contracts):
    return ContractStatsService.get_par_data(contracts)


def get_ratio_of_clients_on_time(Clients):
    ontime_clients = getActiveClientCount(Clients)
    late_clients = getInactiveClientCount(Clients)
    total_count = ontime_clients + late_clients
    if total_count != 0:
        return ontime_clients / total_count
    else:
        return None


def getRecentlyRegisteredClients(Clients, days=90):
    recentDate = datetime.now() - timedelta(days=days)
    recentClients = Clients.filter(lambda C: C.RegistrationDate >= recentDate)
    return recentClients


def getClientsRegisteredInPeriod(Clients, fromDate, toDate):
    return Clients.filter(lambda C: C.RegistrationDate > fromDate and C.RegistrationDate <= toDate)


def getClientsRegisteredInPeriodCount(Clients, fromDate, toDate):
    return getClientsRegisteredInPeriod(Clients, fromDate, toDate).count()


def getClientsDroppedInPeriod(Clients, fromDate, toDate):
    return Clients.filter(lambda c: (toDate >= c.termination_date)
                          and (fromDate < c.termination_date))


def getClientsDroppedInPeriodCount(Clients, fromDate, toDate):
    return getClientsDroppedInPeriod(Clients, fromDate, toDate).count()

