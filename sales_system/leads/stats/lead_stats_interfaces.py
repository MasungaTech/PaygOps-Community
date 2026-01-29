from sales_system.leads.stats.lead_stats import getCurrentLeadCount, getNewLeadInPeriodCount


def bindStatsToEntityWithLeads(entityWithLeads):
    entityWithLeads.getCurrentLeadCount = leads_getCurrentLeadCount
    entityWithLeads.getNewLeadInPeriodCount = leads_getNewLeadInPeriodCount


def leads_getNewLeadInPeriodCount(self, fromDate, toDate):
    return getNewLeadInPeriodCount(self.get_leads(), fromDate, toDate)


def leads_getCurrentLeadCount(self):
    return getCurrentLeadCount(self.get_leads())
