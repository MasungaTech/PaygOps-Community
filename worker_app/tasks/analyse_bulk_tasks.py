import config
from core_system.role.methods.getters import get_role_name_from_id
from core_system.users.models.user_model import User
from shared.logger.loggers import Error
from shared.services.background_task_base import BackgroundTask
from pony import orm
from worker_app.worker_app import worker_app

from task_system.services.task_category_service import TaskCategoryService
from task_system.services.task_system_service import TaskService

HEADER = ['Task Name', 'Notes', 'Deadline', 'Task Category ID', 'Assignee']


@worker_app.task()
@orm.db_session
def analyse_bulk_tasks(task_uuid):

    print('Analysing bulk tasks...')
    task_service = BackgroundTask(task_uuid)
    acting_user = User.get(id=task_service.user)
    file = task_service.read_csv_file()

    correct_tasks = 0
    total_tasks = 0
    data = []
    errors = {}
    task_counts = { }

    for line in file:
        if total_tasks == 0 and [h.lower().strip() for h in line] == [h.lower().strip() for h in HEADER]:
            continue
        total_tasks += 1
        if not(len(line) <= 5):
            errors[total_tasks] = f'Incorrect format, the row must have 5 columns.'
            continue

        task_name = line[0]
        notes = line[1]
        deadline = line[2]
        task_category_id = line[3]
        assignee = line[4]
        

        task_dict = {
            'task_name': task_name,
            'notes': notes,
            'task_type': task_category_id,
            'deadline': deadline,
            'assignee': assignee
        }
        try:
            user = User.get(id=task_service.user)
            if not task_category_id.isnumeric():
                raise Error("Invalid Task category ID")
            task_category = TaskCategoryService.get_from_user_and_id(user, task_category_id)
            if not task_category:
                 raise Error(f'Task Category with ID #{task_category_id} not found')
            TaskService.validate_data(task_dict, acting_user)
        except Error as e:
            errors[total_tasks] = str(e.get_message())
            continue
        correct_tasks += 1
        task_counts[task_category] = 1 if task_category not in task_counts.keys() else task_counts.get(task_category) + 1
        data.append(task_dict)

    task_service.complete_analysis({
        'correct_tasks': correct_tasks,
        'total_tasks': total_tasks,
        'errors': errors,
        'task_counts': task_counts,
    }, data)