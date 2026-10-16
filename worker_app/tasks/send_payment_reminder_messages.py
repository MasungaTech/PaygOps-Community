import math
from payg_loan_system.contracts.models.contract_status import ContractStatus
from payg_loan_system.contracts.models.contract_model import Contract
from pony import orm
import datetime

from worker_app.worker_app import worker_app
from shared.logger.loggers import LogAPI
from shared.services.settings_service import SettingsService
import config
from messages_system.services.send_sms import SMSSend
from messages_system.services.message_service import MessageService


sms_sender = SMSSend
PAGE_SIZE = 10

@worker_app.task
def send_payment_reminder_sms_now():
    if config.DISABLE_HEAVY_TASKS:
        return 
    print('Sending payment reminder SMSs...')
    try:
        send_payment_reminder_sms()
    except Exception as exception:
        LogAPI().FatalNoRequest(exception)
        print('Error when sending payment reminder SMSs: '+repr(exception))
    else:
        print('Done with sending payment reminder SMSs!')


def send_payment_reminder_sms():
    with orm.db_session:
        if not SettingsService.get_setting('SendPaymentReminderMessages'):
            print('The automatic sending of payment reminder SMS is disabled in the config.')
            return
        days = SettingsService.get_setting('PaymentRemindersDaysBeforeExpiry')

    for reminder_day in days:
        send_payment_reminder_sms_at_day_x(reminder_day)

def send_payment_reminder_sms_at_day_x(days_before_expiry):
    if days_before_expiry < 0:
        message_type = 'PAYMENT_REMINDER_SMS_PAST'
    elif days_before_expiry == 0:
        message_type = 'PAYMENT_REMINDER_SMS_TODAY'
    elif days_before_expiry == 1:
        message_type = 'PAYMENT_REMINDER_SMS_TOMORROW'
    else:
        message_type = 'PAYMENT_REMINDER_SMS_SOON'

    today = datetime.date.today() + datetime.timedelta(days=days_before_expiry)  # Today+X at 00:00
    tomorrow = datetime.date.today() + datetime.timedelta(days=days_before_expiry+1)  # Tomorrow+X at 00:00

    with orm.db_session(optimistic=False):
        all_late_contracts = orm.select(
            contract for contract in Contract
            if contract.status == ContractStatus.active
            and contract.next_repayment_due_time >= today
            and contract.next_repayment_due_time < tomorrow
        ).order_by(lambda c: c.id)
        number_of_pages = math.ceil(all_late_contracts.count() / PAGE_SIZE)
        for page_n in range(1, number_of_pages+1):
            print('Page: ' + str(page_n) + ' out of ' + str(number_of_pages))
            with orm.db_session(optimistic=False, strict=True):
                page_data = all_late_contracts.page(page_n, PAGE_SIZE)
                for contract in page_data:
                    send_sms_for_contract(contract, message_type, days_before_expiry)
                orm.commit()
                orm.rollback() # We do that to free memory

def send_sms_for_contract(contract, message_type, days_before_expiry):
    this_client = contract.client
    this_person = this_client.person
    maturity_date = contract.get_date_of_maturity_without_lateness()
    MessageService.send_answer_to_person({
        'status': message_type,
        'days_before_expiry': abs(days_before_expiry),
        'name': this_person.name,
        'surname': this_person.surname,
        'contract_reference': contract.reference,
        'client_phone_number': contract.client.person.preferred_phone_number() or '',
        'device_serial': str(contract.linked_device.get_display_name()) if contract.linked_device else None,
        'offer_name': contract.offer.name,
        'pending_amount': contract.pending_amount,
        'reference_payment': contract.reference_price_at(cached=True),
        'next_payment_price': contract.next_payment_price(cached=True),
        'minimum_payment': contract.minimum_payment,
        'amount_in_arrears': contract.get_net_cumulative_amount_in_arrears(cached=True) or 0,
        'expected_maturity_day': maturity_date.strftime('%d') if maturity_date else '',
        'expected_maturity_month': maturity_date.strftime('%m') if maturity_date else '',
        'expected_maturity_year': maturity_date.strftime('%Y') if maturity_date else ''
    }, this_person)
