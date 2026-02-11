import random
from shared.services.settings_service import SettingsService
from shared.logger.loggers import Error
from pony.orm import flush, rollback
from datetime import datetime
from decimal import Decimal
from payg_loan_system.requests.models import MentorRequest
from payg_loan_system.payments.models.payment import Payment
from payg_loan_system.payments.services.payment_processor_service import PaymentProcessorService


def generate_payment_reference():
    return ''.join(random.choice('0123456789abcdef') for i in range(4)) + '-' + ''\
           .join(random.choice('0123456789abcdef') for i in range(4))


def collect_cash(acting_user, amount, paying_client=None, lead=None, commission=0, time=None, note=''):

    person = (paying_client or lead).person
    if not acting_user.can_access('CollectCashActions', person=person):
        raise Error('INSUFFICIENT_PERMISSION', permission='CollectCashActions')

    if acting_user.cash_allowance is not None and acting_user.cash_allowance < amount:
        raise Error('CASH_COLLECTION_LIMIT_EXCEEDED', cash_allowance=acting_user.cash_allowance)

    paying_account = (paying_client or lead).get_cash_account()
    receiving_account = acting_user.get_cash_account()

    reference_made = generate_payment_reference()
    reference_received = generate_payment_reference()
    now = datetime.now()

    net_amount_paid = amount - commission
    net_amount_paid = Decimal("{:.2f}".format(net_amount_paid))

    if not note:
        note = ''

    try:
        payment_made = Payment(Amount=net_amount_paid, Reference=reference_made, wallet_operator='cash',
                        PaymentTime=time or now, PaymentReceptionTime=now, PaymentWallet=paying_account, processed=True, memo=note)
        flush()
    except Error as e:
        rollback()
        raise e
        
    Payment(Amount=amount, Reference=reference_received, back_payment=payment_made, wallet_operator='cash_collection',
            PaymentTime=now, PaymentReceptionTime=now, PaymentWallet=receiving_account, processed=True, memo=note)

    if paying_client:
        answer = [{'success': True, 'status': 'CASH_PAYMENT_SUCCESS_CLIENT', 'name': paying_client.person.name,
                   'surname': paying_client.person.surname, 'client_id':  paying_client.id, 'amount': amount,
                   'transaction_id': reference_made, 'commission': commission}]
    elif lead:
        answer = [{'success': True, 'status': 'CASH_PAYMENT_SUCCESS_LEAD', 'name': lead.person.name,
                   'surname': lead.person.surname, 'lead_id':  lead.id, 'amount': amount,
                   'transaction_id': reference_made, 'commission': commission}]
    else:
        raise Exception('Cash collection requires either lead or client')

    thresholds = [SettingsService.get_setting('CashCollectionPercentageWarning')/Decimal(100)*(acting_user.cash_limit_overall or 0),
                  SettingsService.get_setting('CashCollectionAmountWarning')]
    if SettingsService.get_setting('CashCollectionLimitEnabled') and any(acting_user.total_cash_collected >= t for t in thresholds if t):
        answer.append({
            'success': True,
            'status': 'CASH_COLLECTION_THRESHOLD_SURPASSED',
            'cash_allowance': acting_user.cash_allowance
        })

    return answer, payment_made


def handle_paycash_request(acting_user, amount, this_device, commission=0,
                           registration_request_code=None, offline=False, time=None, note=''):

    contract = this_device.contract
    if not contract:
        return {'success': False,
                'status': 'DEVICE_NOT_REGISTERED'}

    paying_client = contract.client
    if not note:
        note = ''
    
    try:
        answer, payment_made = collect_cash(acting_user=acting_user, paying_client=paying_client,
                                            amount=amount, commission=commission, time=time, note=note)
    except Error as error:
        return [dict({'success': False, 'status': str(error)}, **error.data)]

    # We store the action
    if registration_request_code is None:
        registration_request_code = str(this_device.composed_serial)
    MentorRequest(ReceptionTime=datetime.now(), Type='Cash Payment', RequestCode=registration_request_code,
                  client=paying_client, Device=this_device, user=acting_user,
                  AdditionalData='Amount Paid:' + str(amount) + ',Reference:' + payment_made.Reference +
                  ',Commission:' + str(commission))

    answer += PaymentProcessorService.process_payment_for_target(
        payment_made,
        contract,
        reprocessing=False,
        error_handler=None
    )
    return answer
