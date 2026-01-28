from pony import orm

from core_system.operational_entities.services.edit_client_group_service import \
    EditClientGroupService
from core_system.users.models.user_model import User
from shared.logger.loggers import Error
from shared.services.background_task_base import BackgroundTask
from worker_app.worker_app import worker_app

HEADER = ['Client Group ID', 'User in Charge ID']


@worker_app.task()
@orm.db_session
def analyse_bulk_edit_client_groups(task_uuid):
    
        print('Analysing bulk update client group...')
        task_service = BackgroundTask(task_uuid)
        file = task_service.read_csv_file()
        acting_user = acting_user = User.get(id=task_service.user)
        correct_cg = 0
        total_cg = 0
        data = []
        errors = {}
        cg_counts = {}
    
        for line in file:
            if len(line) == 2:
                if total_cg == 0 and [h.lower().strip() for h in line] == [h.lower().strip() for h in HEADER]:
                    continue
                total_cg += 1
                client_group_id = line[0]
                user_in_charge_id = line[1]
                cg_dict = {
                    'client_group_id': client_group_id,
                    'user_in_charge_id': user_in_charge_id
                }
            else:
                errors[total_cg] = f'Incorrect format, the row must have two columns'
                continue
            try:
                EditClientGroupService.validate_data(acting_user, cg_dict, for_edit=True)
                correct_cg += 1
            except Error as e:
                errors[total_cg] = e.get_message()
            data.append(cg_dict)

        task_service.complete_analysis({
            'correct_cg': correct_cg,
            'total_cg': total_cg,
            'errors': errors,
            'cg_counts': cg_counts,
        }, data)