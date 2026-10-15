import config
import json
from payg_loan_system.payments.services.payment_getter_service import PaymentGetterService
from payg_loan_system.payments.services.payment_router_service import PaymentRouterService
from datetime import datetime
from pony.orm.core import MultipleObjectsFoundError
from shared.logger.loggers import Error


class ManualPaymentEntryService:

    @classmethod
    def add_manual_payment(cls, current_user, request, amount, reference, reception_time, account_name,
                           account_msisdn=None, memo=None, wallet_operator=None, user_ip=None, user_agent=None):
        if not user_ip:
            user_ip = str(request.environ.get('HTTP_X_REAL_IP', request.remote_addr))
        if not user_agent:
            user_agent = str(request.user_agent)
        if wallet_operator == 'Empty':
            wallet_operator = ''
        # We log the attempt
        manual_payment_log = {
            'user_name': current_user.full_name,
            'user_id': current_user.id,
            'user_agent': user_agent,
            'time': datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            'payment_ref': reference,
            'amount': str(amount),
            'mpesa_name': account_name,
            'account_msisdn': account_msisdn,
            'user_ip': user_ip,
            'memo': memo,
            'wallet_operator': wallet_operator
        }

        # We write the log
        file = open(config.MANUAL_PAYMENT_LOG_PATH, 'a')
        file.write(json.dumps(manual_payment_log) + '\n')
        file.close()

        # We send the data to the payment handler
        PaymentRouterService().handle_payment(
            reference=reference,
            amount=amount,
            sent_datetime=reception_time,
            sender_name=account_name,
            sender_phone_number=account_msisdn,
            memo=memo,
            wallet_operator=wallet_operator
        )

    @classmethod
    def payment_exists(cls, reference, user, wallet_operator=None):
        return PaymentGetterService.get_from_user_and_properties(user, Reference=reference.strip(), wallet_operator=wallet_operator) or PaymentGetterService.get_from_user_and_properties(user, Reference=reference.strip(), wallet_operator='')
