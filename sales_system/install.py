from pony import orm
from sales_system.leads.models.reasons_for_not_buying import ReasonsForNotBuying
from config import REASONS_FOR_NOT_BUYING



@orm.db_session
def create_reasons_for_not_buying():
    for reason in REASONS_FOR_NOT_BUYING:
        if not ReasonsForNotBuying.get(id=reason):
            print('Creating reason: '+str(REASONS_FOR_NOT_BUYING[reason]))
            ReasonsForNotBuying(
                id=reason,
                name=REASONS_FOR_NOT_BUYING[reason]
            )
