from pony import orm
from core_system.client.services.client_getter_service import ClientGetterService

from core_system.users.models.user_model import User
from sales_system.leads.services.edit_lead_service import EditLeadService
from sales_system.leads.services.lead_getter_service import LeadGetterService
from shared.logger.loggers import Error
from shared.services.background_task_base import BackgroundTask
from worker_app.worker_app import worker_app

HEADER = ['Lead ID', 'L0 Entity ID']


@worker_app.task()
@orm.db_session
def analyse_bulk_edit_leads(task_uuid):

    print('Analysing bulk edit leads...')
    task_service = BackgroundTask(task_uuid)
    file = task_service.read_csv_file()

    correct_leads = 0
    total_leads = 0
    data = []
    errors = {}
    leads_counts = {}

    for line in file:
        if len(line) == 2:
            if total_leads == 0 and [h.lower().strip() for h in line] == [h.lower().strip() for h in HEADER]:
                continue
            total_leads += 1
            lead_id = line[0]
            entity_id = line[1]
            lead_dict = {
                'l0_entity_id': entity_id
            }
        else:
            errors[total_leads] = f'Incorrect format, the row must have either two or six columns'
            continue
        try:
            user = User.get(id=task_service.user)
            if not lead_id.isnumeric():
                raise Error("Invalid Lead ID")
            lead = LeadGetterService.get_from_user_and_id(user, lead_id)
            if not lead:
                client = ClientGetterService.get_from_user_and_id(user, lead_id)
                client_found_msg = f'. Client "{client.full_name}" has ID #{lead_id}. Did you mean to move the client instead?' if client else ''
                raise Error(f'Lead with ID #{lead_id} not found' + client_found_msg)
            EditLeadService.validate_data(lead, lead_dict, user)
        except Error as e:
            errors[total_leads] = e.get_message()
            continue
        correct_leads += 1
        leads_counts[entity_id] = 1 if entity_id not in leads_counts.keys() else leads_counts.get(entity_id) + 1
        data.append([lead_id, lead_dict])

    task_service.complete_analysis({
        'correct_leads': correct_leads,
        'total_leads': total_leads,
        'errors': errors,
        'leads_counts': leads_counts,
    }, data)