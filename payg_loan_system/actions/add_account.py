from payg_loan_system.requests.models import MentorRequest
from payg_loan_system.payments.models.payment import Payment
from payg_loan_system.devices.device_api.device_getter_service import *
from payg_loan_system.actions.helpers.code_error import handle_device_code_error, ConfigurationError
from pony.orm import db_session
from datetime import datetime
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService
from payg_loan_system.payments.models.wallet import PaymentWalletOwner


def handle_add_account_request(acting_user, registration_request_code, transaction_reference):

    answer = []

    # We get the device from the registration code
    try:
        this_device = DeviceGetterService.get_device_from_registration_code(registration_request_code)
    except DeviceAPIError as CE:
        return [handle_device_code_error(CE)]  # We call the generic code error handler here to give a readable output
    except ConfigurationError as config_error:
        return [{'success': False,
                'status': 'CONFIGURATION_ERROR',
                'error_type': str(config_error)}]

    this_client = this_device.contract.client if this_device.contract else None
    if this_client == None:
        return [{'success': False,
                'status': 'DEVICE_NOT_REGISTERED'}]

    # We conform the MPESA Ref and input the code
    payment_reference = transaction_reference.upper()

    # We check if the payment is valid
    PaymentToRegister = Payment.get(Reference=payment_reference)
    if (PaymentToRegister is None):
        return [{'success': False,
                'status': 'INVALID_PAYMENT_REFERENCE'}]

    AccountToLink = PaymentToRegister.PaymentWallet

    # We check if the MPESA account is linked already
    if AccountToLink.client is not None:
        answer.append({'status': 'ACCOUNT_ALREADY_LINKED',
                       'account_name': AccountToLink.FullName,
                       'old_account_owner_name': AccountToLink.client.full_name,
                       'old_account_owner_id': AccountToLink.client.id})

    # All OK. We get the account and link it to the owner

    AccountToLink.client = this_client
    create_payment_wallet_owner(AccountToLink, this_client, acting_user)

    answer.append({'success': True,
                   'status': 'ACCOUNT_LINKING_SUCCESS',
                   'account_owner_name': this_client.full_name,
                   'account_owner_id': this_client.id,
                   'account_name': AccountToLink.FullName})

    # We store a trace of the action
    create_mentor_request(registration_request_code,
                          acting_user,
                          this_device,
                          this_client,
                          AccountToLink)

    return answer


def create_payment_wallet_owner(AccountToLink, this_client, acting_user):
    PaymentWalletOwner(
        wallet=AccountToLink,
        client=this_client,
        lead=None,
        approver=acting_user,
        date=datetime.now(),
        balance=AccountToLink.get_balance()
    )


@db_session
def create_mentor_request(reg_req_code, user, device, client, account):
    return MentorRequest(ReceptionTime=datetime.now(),
                         Type='Add MPESA Account',
                         RequestCode=reg_req_code,
                         ActivationTimeAddedInDays=0,
                         CreditsAdded=0,
                         user=user,
                         Device=device,
                         client=client,
                         AdditionalData='MPESA Name:' + account.FullName)
