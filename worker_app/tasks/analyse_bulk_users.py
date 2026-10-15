from core_system.role.methods.getters import get_role_name_from_id
from core_system.users.models.user_model import User
from core_system.users.services.edit_user_service import EditUserService
from shared.logger.loggers import Error
from shared.services.background_task_base import BackgroundTask
from pony import orm
from worker_app.worker_app import worker_app

HEADER = ['Role', 'Reference Entity', 'First Name', 'Surname', 'Username', 'Email', 'Login Expiration Date', 'Cash collection limit', 'Phone Numbers', 'Web & Messages Language', 'Organization', 'Mobile App PIN', 'Create Lead Generator', 'Lead Generator Type', 'Preferred Password Communication']


@worker_app.task()
@orm.db_session
def analyse_bulk_users(task_uuid):

    print('Analysing bulk users...')
    task_service = BackgroundTask(task_uuid)
    acting_user = User.get(id=task_service.user)
    file = task_service.read_csv_file()

    correct_users = 0
    total_users = 0
    data = []
    errors = {}
    role_counts = {

    }

    for line in file:
        if total_users == 0 and [h.lower().strip() for h in line] == [h.lower().strip() for h in HEADER]:
            continue
        total_users += 1
        if not(len(line) <= 15):
            errors[total_users] = f'Incorrect format, the row must have 15 columns.'
            continue

        role_id = line[0]
        reference_entity_id = line[1]
        first_name = line[2]
        surname = line[3]
        username = line[4]
        email = line[5] 
        login_expiration_date = line[6]
        cash_collection_limit = line[7]
        phone_numbers = line[8]
        web_messages_language = line[9]
        organization = line[10]
        mobile_app_pin = line[11]
        create_lead_generator = line[12]
        lead_generator_type = line[13]
        preferred_password_communication = line[14]
        user_dict = {
            'role_id': role_id,
            'reference_entity_id': reference_entity_id,
            'name': first_name,
            'surname': surname,
            'username': username,
            'email': email,
            'login_expiration_date': login_expiration_date,
            'cash_collection_limit': cash_collection_limit,
            'phone_numbers': phone_numbers.split(',') if phone_numbers else [],
            'web_messages_language': web_messages_language,
            'organization': organization,
            'mobile_app_pin': mobile_app_pin,
            'lead_generator_type': lead_generator_type if create_lead_generator.lower() != 'false' else '',
            'preferred_password_communication': preferred_password_communication,
            'auto_generate_password': True
        }
        try:
            EditUserService.validate_data(user_dict, acting_user)
        except Error as e:
            errors[total_users] = str(e.get_message())
            continue
        correct_users += 1
        role_name = get_role_name_from_id(role_id)
        role_counts[role_name] = role_counts.get(role_name, 0) + 1
        data.append(user_dict)

    task_service.complete_analysis({
        'correct_users': correct_users,
        'total_users': total_users,
        'errors': errors,
        'role_counts': role_counts,
    }, data)