from sales_system.leads.services.lead_status_change_service import LeadStatusChangeService
from pony import orm
from sales_system.leads.models.lead import Lead
from worker_app.worker_app import worker_app
from shared.logger.loggers import LogAPI

log_api = LogAPI()


def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))


@worker_app.task
def update_lead_statuses(offer_id=None, status_categories=[]):
    with orm.db_session:
        leads = Lead.select()
        if offer_id:
            leads = leads.filter(lambda l: l.offer.id == offer_id)
        if status_categories:
            leads = leads.filter(lambda l: l.status.category in status_categories)
        
        objects = leads
        count = objects.count()
        ids = orm.select(p.id for p in objects)[:]

    action_name = 'Update Lead Status'
    initial_count = count
    CHUNK_SIZE = 100
    if count > 0:
        print(f'{count} to process for {action_name}')
        for ids_chunk in chunker(ids, CHUNK_SIZE):
            with orm.db_session:
                objs = orm.select(p for p in Lead if p.id in ids_chunk)
                try:
                    for obj in objs:
                        LeadStatusChangeService.update(objs)
                except Exception as e:
                    try:
                        for obj in objs:
                            LeadStatusChangeService.update(obj)
                    except Exception as e:
                        LogAPI.FatalNoRequest(e, extra_data={'task': 'update_lead_statuses'})
                count = count-CHUNK_SIZE
                orm.commit()
                print(f'{count}/{initial_count} left to process for {action_name}')
