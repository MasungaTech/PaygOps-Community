from payg_loan_system.payments.services.b2c_payment_service import B2CPaymentService
from payg_loan_system.payments.services.reconciliation_service import ReconciliationService
from sales_system.leads.services.lead_getter_service import LeadGetterService
from shared.services.settings_service import SettingsService
from shared.logger.loggers import Error
from pony.orm import flush, rollback, commit
from datetime import datetime
from decimal import Decimal
from payg_loan_system.requests.models import MentorRequest
from payg_loan_system.payments.models.payment import Payment
from payg_loan_system.contracts.models.contract_status import ContractStatus
from payg_loan_system.contracts.services.contract_repayment_service import ContractRepaymentService
from payg_loan_system.contracts.services.contract_getter_service import ContractGetterService
from payg_loan_system.actions.collect_cash import generate_payment_reference


def link_payment_to_reconciled_payment(payment, reconciled_payment):
    # This is a weird hack to work around a bug in Pony ORM
    before_update_old = reconciled_payment.before_update
    reconciled_payment.before_update = lambda: None
    reconciled_payment.linked_payment = payment
    flush()
    reconciled_payment.before_update = before_update_old


def pay_client(acting_user, amount, contract, destination, time=None, memo=None, wallet_id=None, wallet_operator=None, downpayment_lead_id=None, contract_to_pay_reference=None):
    if not SettingsService.get_setting('FeatureToggles').get('OffTaking', False):
        raise Error('Offtaking (purchasing add-ons) must be enabled to use this feature')
    
    client = contract.client
    person = client.person
    if not acting_user.can_access('PayClientActions', person=person):
        raise Error('INSUFFICIENT_PERMISSION', permission='PayClientActions')

    if not contract.status == ContractStatus.overpaid or contract.get_outstanding_balance() >= 0:
        raise Error('The contract is not overpaid')
    
    net_amount_paid = Decimal("{:.2f}".format(amount))
    if net_amount_paid <= 0:
        raise Error('Amount paid to client must be positive')
    if abs(net_amount_paid) > abs(contract.get_outstanding_balance()):
        raise Error('You cannot pay more to the client than the amount overpaid on the contract')

    paying_account = client.get_cash_account()
    receiving_account = acting_user.get_cash_account()

    reference_made = generate_payment_reference()
    reference_received = generate_payment_reference()
    now = datetime.now()

    status = 'PAY_CLIENT_SUCCESS_WALLET'
    
    payment_made = None
    reconciled = None
    if destination == 'mobile_money_account':
        status = 'PAY_CLIENT_SUCCESS_MOBILE_MONEY'
        wallet = B2CPaymentService.get_wallet_by_id(wallet_id)
        if not wallet:
            raise Error('Selected wallet not found')
        if wallet.status == 'unavailable':
            raise Error('There is no mobile money integration available that supports sending payment to client')
        operator = wallet.operator if wallet.status == 'active' else wallet_operator
        
        reconciled = ContractRepaymentService.create_off_taking_client_payment(contract, -net_amount_paid, wallet, now)

        payment_data = {
            'amount': net_amount_paid,
            'payment_uuid': reference_made,
            'wallet_operator': operator,
            'wallet_msisdn': wallet.account_phone_number,
            'memo': memo,
            'wallet_name': wallet.FullName
        }
        try:
            payment_made = B2CPaymentService.add_from_data_and_user(payment_data, acting_user)
            link_payment_to_reconciled_payment(payment_made, reconciled)
            answer = [{'success': True, 'status': status, 'name': client.person.name,
                'surname': client.person.surname, 'client_id':  client.id, 'amount': amount, 'account_id': paying_account.id,
                'client_phone_number': wallet.account_phone_number, 'transaction_id': reference_made, 'user_name': acting_user.person.name, 'user_surname': acting_user.person.surname, 'user_id': acting_user.id}]
            return answer, payment_made
        except Error as e:
            rollback()
            raise e 
    else:
        reconciled = ContractRepaymentService.create_off_taking_client_payment(contract, -net_amount_paid, paying_account, now)
        flush()
        
    
    if destination == 'cash_to_client':
        status = 'PAY_CLIENT_SUCCESS_CASH'
        # We take the money from the wallet of the client with the negative payment
        # and do positive on agent wallet
        try:
            payment_made = Payment(Amount=-net_amount_paid, Reference=reference_made, wallet_operator='cash',
                            PaymentTime=time or now, PaymentReceptionTime=now, PaymentWallet=paying_account, processed=True)
            flush()
            payment_made.reconciled_payments.add(reconciled)
        except Error as e:
            rollback()
            raise e
        # We mark that the agent gave money to the client (negative on agent's cash means increase balance)
        Payment(Amount=-net_amount_paid, Reference=reference_received, back_payment=payment_made, wallet_operator='cash_collection',
            PaymentTime=now, PaymentReceptionTime=time or now, PaymentWallet=receiving_account, processed=True)
        link_payment_to_reconciled_payment(payment_made, reconciled)

    if destination == 'lead':
        status = 'PAY_LEAD_SUCCESS_CASH'
        lead = LeadGetterService.get_from_user_and_id(acting_user, id=downpayment_lead_id)
        if not lead:
            raise Error('Downpayment lead not found')
        # We take the money from the wallet of the client with the negative payment
        # and do positive on agent wallet
        try:
            answer = ReconciliationService.get_answer_for_lead(lead, amount=net_amount_paid, account=paying_account, user=acting_user, origin_reconciled_payment=reconciled)
            flush()
            return answer, payment_made
        except Error as e:
            rollback()
            raise e
        
    if destination == 'contract':
        status = 'PAY_CONTRACT_SUCCESS_CASH'
        # We take the money from the wallet of the client with the negative payment
        # and do positive on agent wallet
        contract_to_pay = ContractGetterService.get_from_user_and_properties(acting_user, reference=contract_to_pay_reference)
        if not contract_to_pay:
            raise Error('Contract to pay not found')
        if contract_to_pay == contract:
            raise Error('You cannot pay the contract to itself')
        try:
            answer = ReconciliationService.get_answer_for_contract(contract_to_pay, amount=net_amount_paid, account=paying_account, user=acting_user, origin_reconciled_payment=reconciled)
            flush()
            return answer, payment_made
        except Error as e:
            rollback()
            raise e

    answer = [{'success': True, 'status': status, 'name': client.person.name,
                'surname': client.person.surname, 'client_id':  client.id, 'amount': amount, 'account_id': paying_account.id,
                'transaction_id': reference_made, 'user_name': acting_user.person.name, 'user_surname': acting_user.person.surname, 'user_id': acting_user.id}]
    
    return answer, payment_made


def handle_pay_client_request(acting_user, amount, contract, destination, time=None, memo=None, wallet_id=None, wallet_operator=None, downpayment_lead_id=None, contract_to_pay_reference=None):
    this_device = contract.linked_device
    paying_client = contract.client
    
    try:
        answer, payment_made = pay_client(acting_user=acting_user, amount=amount,
                                            contract=contract, destination=destination, time=time, memo=memo, wallet_id=wallet_id, wallet_operator=wallet_operator, downpayment_lead_id=downpayment_lead_id, contract_to_pay_reference=contract_to_pay_reference)
    except Error as error:
        return [dict({'success': False, 'status': str(error)}, **error.data)]

    # We store the action if there is a device
    if this_device:
        MentorRequest(ReceptionTime=datetime.now(), Type='Pay Client', RequestCode=this_device.composed_serial,
                    client=paying_client, Device=this_device, user=acting_user,
                    AdditionalData='Amount Paid:' + str(amount) + (',Reference:' + payment_made.Reference) if payment_made else '')
    return answer
