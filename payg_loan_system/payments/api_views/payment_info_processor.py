from decimal import Decimal, InvalidOperation
import dateutil
from datetime import datetime

from shared.logger.loggers import Error
from shared.services.settings_service import SettingsService
from pony import orm


class PaymentInfoProcessor:
    
    @staticmethod
    def get_info(payment_data):
        warnings = []
        transaction_id = payment_data.get('transaction_id', payment_data.get('reference')) # For retro-compatibility
        try:
            amount = Decimal(str(payment_data.get('amount')))
            
        except (ValueError, TypeError, InvalidOperation):
            raise Error('The payment amount is not valid')

        if amount <= 0:
            with orm.db_session:
                if not SettingsService.get_setting('FeatureToggles').get('OffTaking', False):
                    raise Error('The payment amount must be more than 0')
        if round(amount, 2) != amount:
            raise Error('INVALID_AMOUNT_TOO_MANY_DIGITS')
        sender_name = payment_data.get('wallet_name', payment_data.get('sender_name')) # For retro-compatibility
        sender_phone_number = payment_data.get('wallet_msisdn', payment_data.get('sender_msisdn', None)) # For retro-compatibility
        if sender_phone_number and '+' not in sender_phone_number:
            try:
                sender_phone_number = '+' + str(int(sender_phone_number))
            except (ValueError, TypeError):
                sender_phone_number = ''
                warnings += ['Invalid wallet_msisdn']
        sent_datetime = payment_data.get('sent_datetime', None)
        if sent_datetime:
            try:
                sent_datetime = dateutil.parser.parse(payment_data['sent_datetime'])
            except ValueError:
                return {'error': 'Field sent_datetime does not match ISO 8601 format'}, 400
        else:
            sent_datetime = datetime.now()
        # We remove the timezone as the API mandates sending in UTC and
        # other timezones could cause issues
        sent_datetime = sent_datetime.replace(tzinfo=None)

        memo = payment_data.get('memo', payment_data.get('note', ''))
        wallet_operator = payment_data.get('wallet_operator', '') or ''
        country = payment_data.get('country', '')
        currency = payment_data.get('currency', '')

        return {
            'transaction_id': transaction_id,
            'amount': amount,
            'sender_name': sender_name,
            'sender_phone_number': sender_phone_number,
            'sent_datetime': sent_datetime,
            'memo': memo,
            'wallet_operator': wallet_operator,
            'country': country,
            'currency': currency,
            'warnings': warnings
        }
