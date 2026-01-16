from datetime import datetime
from decimal import Decimal
from core_system.phone_numbers.services.add_phone_number_service import AddPhoneNumberService
from core_system.users.models.user_model import User
from munch import DefaultMunch
from payg_loan_system.payments.models.wallet import PaymentWallet
from payg_loan_system.payments.services.payment_router_service import PaymentRouterService
from shared.logger.loggers import Error
from shared.services.background_task_base import BackgroundTask
from pony import orm
from worker_app.worker_app import worker_app

HEADER = ['Reference', 'Payment Time', 'Amount', 'Wallet Name', 'Wallet MSISDN', 'Memo', 'Operator']


@worker_app.task
@orm.db_session
def analyse_bulk_payments(task_uuid):

    print('Analysing bulk payments...')
    task_service = BackgroundTask(task_uuid)
    acting_user = User.get(id=task_service.user)
    file = task_service.read_csv_file()

    destinations_counts = {
        'Orphaned': 0,
        'Contract': 0,
        'Lead': 0,
        'Add-On': 0,
        'User': 0
    }
    t = {
        'Contract': 'Contract',
        'Lead': 'Lead',
        'ContractAddOn': 'Add-On',
        'User': 'User'
    }
    correct_payments = 0
    total_payments = 0
    data = []
    errors = {}
    warnings = {}
    duplicate_checker = []

    operators = orm.select(p.operator for p in PaymentWallet)

    for line in file:
        if total_payments == 0 and [h.lower().strip() for h in line] == [h.lower().strip() for h in HEADER]:
            continue
        total_payments += 1
        if not(5 <= len(line) <= 7):
            print(line)
            errors[total_payments] = f'Incorrect format, the row must have between 5 and 7 columns.'
            continue

        reference = line[0]
        reception_time_raw = line[1]
        amount_raw = line[2]
        account_name = line[3]
        account_msisdn = line[4]
        memo = line[5] if len(line) > 5 else ''
        operator = line[6] if len(line) > 6 else ''

        reference = reference.strip()
        if not reference:
            errors[total_payments] = 'Payment reference is missing'
            continue
        else:
            try:
                existing = PaymentRouterService.already_existing_payment(reference, operator)
                if existing:
                    errors[total_payments] = f'A payment with that reference and operator already exists: Ref: "{reference}" / Op: {operator}'
                    continue
            except Error as e:
                errors[total_payments] = e.get_message()
                continue
        
        reception_time = None
        try:
            reception_time = datetime.strptime(reception_time_raw, "%Y-%m-%dT%H:%M:%S")
        except Exception:
            errors[total_payments] = f'Invalid date format {reception_time_raw} for payment "{reference}"'
            continue

        amount = None
        try:
            amount = Decimal(amount_raw)
        except Exception:
            errors[total_payments] = f'Invalid amount format "{reference}"'
            continue
        
        if amount == 0:
            errors[total_payments] = f'Amount canot be 0 for payment "{reference}"'
            continue

        if [operator, reference] in duplicate_checker:
            errors[total_payments] = f'A payment with that reference and operator already in this CSV: Ref: "{reference}" / Op: {operator}'
            continue

        if operator and operator not in operators:
            warnings[total_payments] = f'Operator "{operator}" does not exist so it will be created. Please check spelling if you were expecting it to be already in the platform.'

        duplicate_checker.append([operator, reference])
        correct_payments += 1

        existing_wallet = PaymentWallet.get(FullName=account_name, operator=operator)
        # We always use a fake wallet to be able to modify anything that changes due to that payment (e.g. msisdn)
        if account_msisdn:
            try: AddPhoneNumberService._is_phone_number_valid(account_msisdn)
            except Error: is_valid = False
            else: is_valid = True
        else:
            is_valid = False
        number = DefaultMunch(number=account_msisdn) if is_valid else existing_wallet.phone_number if existing_wallet else None
        
        payment = DefaultMunch(
            PaymentWallet=DefaultMunch(
                FullName=account_name,
                phone_number=number,
                client=existing_wallet.client if existing_wallet else None,
                lead=existing_wallet.lead if existing_wallet else None,
                user=existing_wallet.user if existing_wallet else None,
            ),
            memo=memo,
        )

        destination = PaymentRouterService.find_payment_route(payment)
        name = t[destination.__class__.__name__] if destination else 'Orphaned'
        destinations_counts[name] += 1
        data.append([reference, reception_time.isoformat(), str(amount), account_name, account_msisdn, memo, operator])

    task_service.complete_analysis({
        'correct_payments': correct_payments,
        'total_payments': total_payments,
        'destinations_counts': destinations_counts,
        'errors': errors,
        'warnings': warnings
    }, data)