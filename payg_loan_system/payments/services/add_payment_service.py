from payg_loan_system.payments.services.payment_router_service import PaymentRouterService
from payg_loan_system.payments.api_views.payment_info_processor import PaymentInfoProcessor
from shared.logger.loggers import LogAPI
from pony.orm import db_session
from shared.services.base_service import BaseService


class AddPaymentService(BaseService):

    @classmethod
    def _add_from_data_and_user(cls, payment_data, user):

        LogAPI.Event('Payment received: ' + repr(payment_data))

        data = PaymentInfoProcessor.get_info(payment_data)
        warnings = data['warnings']
        with db_session:
            result = PaymentRouterService.handle_payment(
                reference=data['transaction_id'],
                amount=data['amount'],
                sent_datetime=data['sent_datetime'],
                sender_name=data['sender_name'],
                sender_phone_number=data['sender_phone_number'],
                memo=data['memo'],
                wallet_operator=data.get('wallet_operator') or '',
                country=data['country'],
                currency=data['currency']
            )
        if warnings:
            return result, {'warnings': warnings}
        return result
