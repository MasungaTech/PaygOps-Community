from flask_restful import Resource, request
from shared.api_helpers.server_helpers.jwt_and_schema_verification import verify
from pony.orm import db_session
from payg_loan_system.payments.services.payment_options_service import PaymentOptionsService
from shared.logger.loggers import LogAPI

log_api = LogAPI()


class PaymentOptionsResource(Resource):

    @verify(permissions=['AddPayments'])
    @db_session
    def get(self):
        contract_reference = request.args.get('contract_reference', None)
        device_serial_number = request.args.get('device_serial_number', None)
        client_id = request.args.get('client_id', None)
        phone_number = request.args.get('phone_number', None)
        payment_account_name = request.args.get('wallet_name', request.args.get('payment_account_name', None))

        if contract_reference:
            return PaymentOptionsService.get_from_contract_reference(contract_reference)
        if device_serial_number:
            return PaymentOptionsService.get_from_device_serial_number(device_serial_number)
        if client_id:
            return PaymentOptionsService.get_from_client_id(client_id)
        if phone_number:
            return PaymentOptionsService.get_from_phone_number(phone_number)
        if payment_account_name:
            return PaymentOptionsService.get_from_payment_account_name(payment_account_name)
        return [], 200
