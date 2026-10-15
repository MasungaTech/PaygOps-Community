from data_system.payment_stats import *

def bindPaymentStats(entityWithClients):
    entityWithClients.getTurnoverFromClientsToday = clients_getTurnoverFromClientsToday
    entityWithClients.getTurnoverInPeriod = clients_getTurnoverInPeriod
    entityWithClients.getPaymentsInPeriodCount = clients_getPaymentsInPeriodCount


def clients_getTurnoverFromClientsToday(self):
    return getTurnoverFromClientsToday(self)

def clients_getTurnoverInPeriod(self, fromDate, toDate):
    return getTurnoverInPeriod(self, fromDate, toDate)

def clients_getPaymentsInPeriodCount(self, fromDate, toDate):
    return getPaymentsInPeriodCount(self, fromDate, toDate)
