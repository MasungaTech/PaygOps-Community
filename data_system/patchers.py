from core_system.operational_entities.models import Village
from core_system.core_entities import db
from core_system.operational_entities.models import Cluster
from sales_system.leads.stats.lead_stats_interfaces import bindStatsToEntityWithLeads
from data_system.client_stats_interfaces import bindClientStats
from data_system.payment_stats_interfaces import bindPaymentStats
from data_system.support_stats_interfaces import bindSupportStats, bindIssueStats
from core_system.users.models.user_model import User


def basicStatsBind(Entity):
    bindClientStats(Entity)
    bindStatsToEntityWithLeads(Entity)
    bindPaymentStats(Entity)
    bindSupportStats(Entity)
    bindIssueStats(Entity)

basicStatsBind(db.Hub)
basicStatsBind(Cluster)
basicStatsBind(Village)

bindClientStats(User)
