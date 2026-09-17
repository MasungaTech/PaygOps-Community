from pony import orm
from core_system.client.services.client_edit_service import ClientEditService
from core_system.client.services.client_getter_service import ClientGetterService

from core_system.users.models.user_model import User
from sales_system.leads.services.lead_getter_service import LeadGetterService
from shared.logger.loggers import Error
from shared.services.background_task_base import BackgroundTask
from worker_app.worker_app import worker_app

HEADER = ['Client ID', 'L0 Entity ID']


@worker_app.task()
@orm.db_session
def analyse_bulk_edit_clients(task_uuid):

    print('Analysing bulk edit clients...')
    task_service = BackgroundTask(task_uuid)
    file = task_service.read_csv_file()

    correct_clients = 0
    total_clients = 0
    data = []
    errors = {}
    clients_counts = {}

    for line in file:
        if len(line) == 2:
            if total_clients == 0 and [h.lower().strip() for h in line] == [h.lower().strip() for h in HEADER]:
                continue
            total_clients += 1
            client_id = line[0]
            entity_id = line[1]
            client_dict = {
                'l0_entity_id': entity_id
            }
        else:
            errors[total_clients] = f'Incorrect format, the row must have either two or six columns'
            continue
        try:
            user = User.get(id=task_service.user)
            if not client_id.isnumeric():
                raise Error("Invalid client ID")
            client = ClientGetterService.get_from_user_and_id(user, client_id)
            if not client:
                lead = LeadGetterService.get_from_user_and_id(user, client_id)
                lead_found_msg = f'. Lead "{lead.full_name}" has ID #{client_id}. Did you mean to move the lead instead?' if lead else ''
                raise Error(f'Client with ID #{client_id} not found' + lead_found_msg)
            ClientEditService.validate_data(client, client_dict, user)
        except Error as e:
            errors[total_clients] = e.get_message()
            continue
        correct_clients += 1
        clients_counts[entity_id] = 1 if entity_id not in clients_counts.keys() else clients_counts.get(entity_id) + 1
        data.append([client_id, client_dict])

    task_service.complete_analysis({
        'correct_clients': correct_clients,
        'total_clients': total_clients,
        'errors': errors,
        'clients_counts': clients_counts,
    }, data)