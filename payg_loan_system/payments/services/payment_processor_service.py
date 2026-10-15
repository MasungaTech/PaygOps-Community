from payg_loan_system.payments.models.payment import Payment
from shared.api_helpers.hook_helpers.process_hook import add_hook_after_commit, process_hook
from core_system.users.models.user_model import User
from sales_system.leads.models.lead import Lead
from payg_loan_system.contracts.models.addons_model import ContractAddOn
from payg_loan_system.contracts.models.contract_model import Contract
from payg_loan_system.payments.services.reconciliation_service import ReconciliationService
from messages_system.services.message_service import MessageService
from shared.services.settings_service import SettingsService
from shared.helpers.numbers import round_if_exists
from shared.logger.loggers import Error
from pony.orm import db_session
from core_system.core_entities import db


class PaymentProcessorService:

    targets_info = {
        Lead: {
            'handler': 'get_answer_for_lead',
            'params': lambda lead, payment: [lead, payment],
            'receiver': lambda lead: lead.person,
            'hook': 'new_lead_payment'
        },
        Contract: {
            'handler': 'get_answer_for_contract',
            'params': lambda contract, payment: [contract, payment],
            'receiver': lambda contract: contract.client.person,
            'hook': 'new_contract_payment'
        },
        ContractAddOn: {
            'handler': 'get_answer_for_addons',
            'params': lambda addon, payment: [addon.contract, [addon], payment],
            'receiver': lambda addon: addon.contract.client.person,
            'hook': 'new_addon_payment'
        },
        User: {
            'handler': 'get_answer_for_user',
            'params': lambda user, payment: [user, payment],
            'receiver': lambda user: user.person,
            'hook': 'new_user_payment'
        }
    }

    @classmethod
    def process_payment_for_target(cls, payment, target, reprocessing, error_handler):
        target_info = cls.targets_info[target.__class__]
        if not target_info:
            raise Exception('UNKNOWN_MATCHING_TARGET')
        answer = cls._get_answer_catching_errors(target_info['handler'], *target_info['params'](target, payment), error_handler=error_handler)
        answer = cls.compile_and_send_answer(target_info['receiver'](target), payment, answer, reprocessing)
        if answer:
            add_hook_after_commit(db, target_info['hook'], payment.get_serialized_object())
        return answer

    @staticmethod
    def _get_answer_catching_errors(processor, *args, error_handler=None):
        try:
            return getattr(ReconciliationService, processor)(*args)
        except Error as error:
            if not error_handler:
                raise error
            error_handler(error)

    @classmethod
    @db_session
    def process_orphaned_payment(cls, payment):
        Payment.get(id=payment.id).processed = True
        status = {
            'success': True,
            'status': 'PAYMENT_RECEIVED_UNKNOWN',
            'amount': round_if_exists(payment.Amount),
            'balance': round_if_exists(payment.PaymentWallet.get_balance()),
            'transaction_id': payment.Reference
        }
        cls._send_message_from_status(status, payment)
        add_hook_after_commit(db, 'new_orphaned_payment', payment.get_serialized_object())

    @classmethod
    def _send_message_from_status(cls, status, payment, person=None):
        recipient_mode = SettingsService.get_setting('MessageRecipient')
        sms = None
        if recipient_mode in ['PERSON_NUMBER', 'BOTH']:
            sms = MessageService.send_answer_to_person(status, person)
        wallet = payment.PaymentWallet
        payment_number = getattr(wallet.phone_number, 'number', '')
        equal_phones = sms and cls._are_phone_number_equal(sms.ToNumber, payment_number)
        if recipient_mode in ['PAYMENT_NUMBER', 'BOTH'] and payment_number and not equal_phones:
            MessageService.send_answer_to_person(status, person, payment_number)

    @classmethod
    def _are_phone_number_equal(cls, number_1, number_2):
        clean = lambda x: '+'+str(int(x or 0))
        return clean(number_1) == clean(number_2)

    @classmethod
    def _get_payment_received_status(cls, payment, person):
        return {
            'success': True,
            'status': 'PAYMENT_RECEIVED',
            'amount': round_if_exists(payment.Amount),
            'balance': round_if_exists(payment.PaymentWallet.get_balance()),
            'name': person.name,
            'surname': person.surname,
            'transaction_id': payment.Reference
        }

    @classmethod
    def compile_and_send_answer(cls, person, payment, answer, reprocessing):
        if not reprocessing:
            reprocessing_answer = [cls._get_payment_received_status(payment, person)]
            if answer:
                answer = reprocessing_answer + answer
            else:
                answer = reprocessing_answer
        else:
           answer = cls._clean_answer_if_reprocessing(answer)
        if answer:
            cls._send_message_from_status(answer, payment, person)
        return answer
    
    @classmethod
    def _clean_answer_if_reprocessing(cls, answer):
        MESSAGES_NOT_REPROCESSABLE = ['LOAN_OVERPAYMENT']
        clean_answer = []
        if isinstance(answer, list):
            for a in answer:
                ca = cls._clean_answer_if_reprocessing(a)
                if ca:
                    clean_answer.append(ca)
        else:
            if answer and answer.get('status') not in MESSAGES_NOT_REPROCESSABLE:
                clean_answer = answer
        return clean_answer
