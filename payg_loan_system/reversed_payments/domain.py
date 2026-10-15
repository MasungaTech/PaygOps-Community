from datetime import datetime
import random

from shared.helpers.date_helper import parse_datetime



class PaymentReversal:
    ISO_PATTERN = '%Y-%m-%dT%H:%M:%S.%fZ'

    reference = ''
    payment_reference = ''
    sent_datetime = None
    sender_msisdn = ''
    sender_name = ''
    amount = None
    wallet_operator = ''

    def __init__(self, reference, payment_reference, sent_datetime=None, wallet_operator='', sender_msisdn='', sender_name='', amount=None):
        self.reference = reference
        self.payment_reference = payment_reference
        if sent_datetime:
            self.sent_datetime = parse_datetime(sent_datetime)
        else:
            self.sent_datetime = datetime.now()
        self.sender_msisdn = sender_msisdn
        self.sender_name = sender_name
        self.amount = amount
        self.wallet_operator = wallet_operator

    def add_sender_msisdn(self, sender_msisdn):
        self.sender_msisdn = sender_msisdn

    def add_sender_name(self, sender_name):
        self.sender_name = sender_name

    def add_amount(self, amount):
        self.amount = amount
    
    def add_wallet_operator(self, wallet_operator):
        self.wallet_operator = wallet_operator

    def serialize(self):
        return self.__dict__
    
    @classmethod
    def generate_reference(cls):
        return ''.join(random.choice('0123456789abcdef') for i in range(4)) + '-' + ''\
            .join(random.choice('0123456789abcdef') for i in range(4))

    @classmethod
    def deserialize(cls, descriptor):
        return cls(descriptor.get('reversal_transaction_id', descriptor.get('reference', cls.generate_reference())),
                   descriptor.get('payment_transaction_id', descriptor.get('payment_reference')),
                   descriptor.get('sent_datetime', None) , descriptor.get('wallet_operator', ''))
