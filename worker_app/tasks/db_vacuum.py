from pony.orm import db_session
from core_system.users.models.user_model import User
from sales_system.leads.models.lead import Lead
from sales_system.leads.services.edit_lead_service import EditLeadService
from worker_app.worker_app import worker_app
from shared.model.activity_log_db import audit_db
from shared.logger.loggers import LogService


@worker_app.task
def db_vacuum(*args, **kwargs):
    with db_session:
        con = audit_db.get_connection()
        con.set_isolation_level(0)
        cur = con.cursor()
        cur.execute('VACUUM FULL;')
    LogService.Warning('Finished vaccuuming.')

