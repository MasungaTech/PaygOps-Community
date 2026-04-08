from .support_stats import *


def bindSupportStats(entityWithClients):
    entityWithClients.getPhysicalVisitsInPeriodCount = clients_getPhysicalVisitsInPeriodCount
    entityWithClients.getPhoneCallsInPeriodCount = clients_getPhoneCallsInPeriodCount
    entityWithClients.hasOpenIssueReport = clients_hasOpenIssueReport


def clients_hasOpenIssueReport(self):
    return hasOpenIssueReport(self.get_clients())

def clients_getPhysicalVisitsInPeriodCount(self, fromDate, toDate):
    return getPhysicalVisitsInPeriodCount(self.get_clients(active=False), fromDate, toDate)


def clients_getPhoneCallsInPeriodCount(self, fromDate, toDate):
    return getPhoneCallsInPeriodCount(self.get_clients(active=False), fromDate, toDate)


def bindIssueStats(entityWithIssue):
    entityWithIssue.getOpenIssueCount = issues_getOpenIssueCount
    entityWithIssue.getNewIssueInPeriodCount = issues_getNewIssueInPeriodCount


def issues_getOpenIssueCount(self):
    return getOpenIssueCount(self.get_clients(active=False))

def issues_getNewIssueInPeriodCount(self, fromDate, toDate):
    return getNewIssueInPeriodCount(self.get_clients(active=False), fromDate, toDate)