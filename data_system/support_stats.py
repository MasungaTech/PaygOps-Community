import config
if config.ENABLE_ENTERPRISE_FEATURES:
    from after_sales_system.interaction_system.model.interaction_report_model import InteractionReport, InteractionMethod
    from after_sales_system.issue_system.model.issue_model import Issue, IssueStatus

from pony.orm import *

def getInteractionsInPeriod(Clients, fromDate, toDate):
    reports = select(I for I in InteractionReport if I.client in Clients)
    return reports.filter(lambda I: I.reportDate > fromDate and I.reportDate <= toDate)


def getPhysicalVisitsInPeriodCount(Clients, fromDate, toDate):
    if not config.ENABLE_ENTERPRISE_FEATURES:
        return 0
    interactions = getInteractionsInPeriod(Clients, fromDate, toDate)
    physicalVisits = interactions.filter(lambda I: I.method == InteractionMethod.visit_at_client)
    return physicalVisits.count()


def getPhoneCallsInPeriodCount(Clients, fromDate, toDate):
    if not config.ENABLE_ENTERPRISE_FEATURES:
        return 0
    interactions = getInteractionsInPeriod(Clients, fromDate, toDate)
    phoneCalls = interactions.filter(lambda I: I.method == InteractionMethod.phone_call)
    return phoneCalls.count()


def getOpenIssueCount(Clients):
    if not config.ENABLE_ENTERPRISE_FEATURES:
        return 0
    issueReports = select(I for I in Issue if I.affectedClient in Clients)
    return issueReports.filter(lambda I: I.status != IssueStatus.solved and
                                         I.status != IssueStatus.wont_solve).count()


def getNewIssueInPeriodCount(Clients, fromDate, toDate):
    if not config.ENABLE_ENTERPRISE_FEATURES:
        return 0
    issueReports = select(I for I in Issue if I.affectedClient in Clients)
    return issueReports.filter(lambda I: I.startDate > fromDate and I.startDate <= toDate).count()


def hasOpenIssueReport(Clients):
    if not config.ENABLE_ENTERPRISE_FEATURES:
        return False
    return (getOpenIssueCount(Clients) != 0)
