from constants import INTEGER_REQUIRED_OPTIONS
from messages_system.services.message_service import MessageService
from payg_loan_system.contracts.models.repayment_discount_types import \
    ContractRepaymentDiscountTypes
from payg_loan_system.contracts.models.repayment_model import ContractRepayment
from payg_loan_system.contracts.services.contract_repayment_service import \
    ContractRepaymentService
from payg_loan_system.transaction_requests.services.transaction_service import \
    BOOLEAN_SCHEMA, TransactionService
from shared.helpers.numbers import round_if_exists
from shared.logger.loggers import Error
from shared.services.settings_service import SettingsService


class ReverseRepaymentService(TransactionService):

    type = 'reverse_repayment'
    permissions = ['HandleReversedPayments']
    description = 'Reverses a repayment given by `repayment_id`'
    schema = {
        "properties": {
            "repayment_id": {
                "oneOf": INTEGER_REQUIRED_OPTIONS,
                "example": 123,
                "description": "The ID of the repayment to be reversed",
                "default": "",
            },
            "send_sms_to_client": {
                **BOOLEAN_SCHEMA,
                **{'description': "Whether the result of the transaction should be sent to the client via SMS"}
            }
        },
        "required": ["repayment_id"]
    }

    @classmethod
    def _validate_data(cls, **kwargs):

        repayment = ContractRepayment.get(id=kwargs['repayment_id'])
        if not repayment:
            raise Error('INVALID_REPAYMENT_ID')

        return {'repayment': repayment, 'client': repayment.contract.client, 'this_device': repayment.contract.linked_device}

    @classmethod
    def _process(cls, user, offline, time, **kwargs):
        repayment = kwargs['repayment']
        person = repayment.contract.client.person
        reversed_repayment = ContractRepaymentService.reverse_repayment(repayment, user)
        if reversed_repayment.discount_type == ContractRepaymentDiscountTypes.downpayment_reversal and not SettingsService.get_setting('EnableContractPaymentsForReversedDownpayments'):
                status = {
                    'success': True,
                    'status': 'PAYMENT_REVERSED_SETTING_DISABLED',
                    'amount': round_if_exists(repayment.amount),
                    'name': person.name,
                    'surname': person.surname,
                    'transaction_id': ', '.join([payment.linked_payment.Reference if payment.linked_payment else '' for payment in repayment.reconciled_payments]),
                    'contract_reference': repayment.contract.reference
                }
                MessageService.send_answer_to_person(status, person=repayment.contract.client.person)
                return [status]
        status = {
            'success': True,
            'status': 'PAYMENT_REVERSED_SETTING_ENABLED',
            'amount': round_if_exists(repayment.amount),
            'name': person.name,
            'surname': person.surname,
            'transaction_id': ', '.join([payment.linked_payment.Reference if payment.linked_payment else '' for payment in repayment.reconciled_payments]),
            'contract_reference': repayment.contract.reference
        }
        MessageService.send_answer_to_person(status, person=repayment.contract.client.person)
        return [status]
