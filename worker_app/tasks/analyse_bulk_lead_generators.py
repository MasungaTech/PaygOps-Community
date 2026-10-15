from pony import orm

from core_system.person.services.edit_person_service import EditPersonService
from core_system.users.models.user_model import User
from sales_system.lead_generator.services.lead_generator_edit_service import LeadGeneratorEditService
from shared.logger.loggers import Error
from shared.services.background_task_base import BackgroundTask
from worker_app.worker_app import worker_app

HEADER = ['First Name', 'Surname', 'Phone numbers', 'Birth Date', 'Gender', 'Lead Generator Type']
HEADER_2 = ['User ID', 'Lead Generator Type']


@worker_app.task()
@orm.db_session
def analyse_bulk_lead_generators(task_uuid):

    print('Analysing bulk lead generators...')
    task_service = BackgroundTask(task_uuid)
    file = task_service.read_csv_file()

    correct_lg = 0
    total_lg = 0
    data = []
    errors = {}
    lg_counts = {}

    for line in file:
        if len(line) == 6:
            if total_lg == 0 and [h.lower().strip() for h in line] == [h.lower().strip() for h in HEADER]:
                continue
            total_lg += 1
            first_name = line[0]
            surname = line[1]
            phone_numbers = line[2]
            birth_date = line[3] 
            gender = line[4]
            lead_generator_type = line[5]
            lg_dict = {
                'name': first_name,
                'surname': surname,
                'birth_date': birth_date,
                'gender': gender,
                'phone_numbers': phone_numbers.split(';') if phone_numbers else [],
                'type': lead_generator_type
            }
        elif len(line) == 2:
            if total_lg == 0 and [h.lower().strip() for h in line] == [h.lower().strip() for h in HEADER_2]:
                continue
            total_lg += 1
            user_id = line[0]
            lead_generator_type = line[1]
            lg_dict = {
                'linked_user_id': user_id,
                'type': lead_generator_type
            }
        else:
            errors[total_lg] = f'Incorrect format, the row must have either two or six columns'
            continue
        try:
            LeadGeneratorEditService.validate_data(lg_dict, User.get(id=task_service.user))
        except Error as e:
            errors[total_lg] = e.get_message()
            continue
        correct_lg += 1
        lg_counts[lead_generator_type] = 1 if lead_generator_type not in lg_counts.keys() else lg_counts.get(lead_generator_type) + 1
        data.append(lg_dict)

    task_service.complete_analysis({
        'correct_lg': correct_lg,
        'total_lg': total_lg,
        'errors': errors,
        'lg_counts': lg_counts,
    }, data)