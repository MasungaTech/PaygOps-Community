

def getCurrentLeadCount(Leads):
    return get_active_leads(Leads).count()


def getNewLeadInPeriodCount(Leads, fromDate, toDate):
    filteredLeads = get_active_leads(Leads).filter(lambda L: L.receptionTime > fromDate and L.receptionTime <= toDate)
    return filteredLeads.count()

def get_active_leads(Leads):
    return Leads.filter(lambda l: l.active)
