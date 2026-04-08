from payg_loan_system.reversed_payments.domain import PaymentReversal
from shared.logger.loggers import LogAPI

log = LogAPI()


class PaymentReversalValidator:
    REQUIRED_FIELDS = ['reference', 'payment_reference']

    @classmethod
    def check_fields(cls, data):
        has_proper_format = cls._check_format(data)

        return has_proper_format

    @staticmethod
    def _check_format(fields):
        try:
            PaymentReversal.deserialize(fields)
        except (KeyError, ValueError) as error:
            log.Event('Bad format: {}'.format(repr(error)))
            return False
        return True
