from psycopg2 import sql

from pony.orm import db_session
import config
from core_system.users.models.user_model import User
from sales_system.leads.models.lead import Lead
from sales_system.leads.services.edit_lead_service import EditLeadService
from worker_app.worker_app import worker_app
from core_system.core_entities import db
from shared.logger.loggers import LogService


@worker_app.task
def reindex(*args, **kwargs):
    with db_session:
        con = db.get_connection()
        con.set_isolation_level(0)
        cur = con.cursor()
        cur.execute(sql.SQL('REINDEX DATABASE {}').format(sql.Identifier(config.MAIN_DB_NAME)))
    LogService.Warning('Finished reindexing')

