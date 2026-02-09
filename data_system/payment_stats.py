from pony import orm
from payg_loan_system.payments.services.payment_getter_service import PaymentGetterService
from datetime import datetime, timedelta
from flask_login import current_user
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService



def getTurnoverFromClientsToday(entity):
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    getTurnoverInPeriod(entity, today, today+timedelta(days=1))


def getTurnoverInPeriod(entity, fromDate, toDate):
    payments_in_period = get_payments_in_period(entity, fromDate, toDate)
    turnover = orm.select(p.amount for p in payments_in_period).sum()
    if turnover:
        return turnover
    return 0


def getPaymentsInPeriodCount(entity, fromDate, toDate):
    return get_payments_in_period(entity, fromDate, toDate).count()


def get_payments_in_period(entity=None, fromDate=None, toDate=None):
    if not entity.entity:
        villages_ids, client_groups_ids = current_user.get_villages_and_client_groups_with_permission('ViewClients', return_villages_ids=True)
    else:
        villages_ids = orm.select(e.id for e in entity.entity.descendants)[:]
        client_groups_ids = []
    return PaymentGetterService.get_reconciled_payments_from_clients_and_leads_in_entities(villages_ids, client_groups_ids, fromDate, toDate)
