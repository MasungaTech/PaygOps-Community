from datetime import datetime

from pony import orm
from pony.orm import db_session

from core_system.phone_numbers.services.add_phone_number_service import \
    AddPhoneNumberService
from payg_loan_system.payments.models.payment import Payment
from payg_loan_system.payments.models.wallet import (PaymentWallet,
                                                     PaymentWalletType)
from payg_loan_system.reversed_payments.models import ReversedPayment
from shared.logger.loggers import Error
from shared.services.settings_service import SettingsService


class PaymentCreationService:

    @classmethod
    @db_session
    def create_payment(cls, reference, amount, sent_datetime, full_name, phone_number=None,
                        memo=None, wallet_operator=None, country=None, currency=None, payment_uuid=None):

        if amount < 0 and not SettingsService.get_setting('FeatureToggles').get('OffTaking', False) and not payment_uuid:
            raise Error('Payments cannot be for an amount less or equal to 0')

        try:

            payment_wallet = cls._get_or_create_payment_wallet(
                full_name, phone_number, wallet_operator
            )
            incoming_payment = Payment(
                Amount=amount,
                Reference=reference,
                PaymentTime=sent_datetime,
                PaymentReceptionTime=datetime.now(),
                PaymentWallet=payment_wallet,
                memo=memo if memo else '',
                wallet_operator=wallet_operator if wallet_operator else '',
                country=country if country else '',
                currency=currency if currency else '',
                payment_uuid=payment_uuid if payment_uuid else reference
            )
            reversal = ReversedPayment.get(
                payment_code=reference.strip(), wallet_operator=wallet_operator or ''
            )
            if reversal:
                reversal.payment = incoming_payment

            orm.commit()  # We need to actually commit here

        except Exception as e:
            orm.rollback()
            raise e
        return incoming_payment

    @classmethod
    def _get_or_create_payment_wallet(cls, full_name, phone_number_str=None, operator=None):
        if not phone_number_str:
            phone_number_str = ''
        if not operator:
            operator = ''

        payment_wallet = PaymentWallet.get(FullName=full_name, operator=operator)
        if payment_wallet is None:
            payment_wallet = cls._create_payment_wallet(
                full_name=full_name,
                phone_number_str=phone_number_str,
                operator=operator
            )
        else:
            if payment_wallet.Type != PaymentWalletType.mobile_money:
                raise Error('Payment Wallet cannot be cash collection wallet')
            if phone_number_str != '':
                payment_wallet.account_phone_number = phone_number_str
            if operator is not None:
                payment_wallet.operator = operator
        AddPhoneNumberService.add_phone_number_to_wallet(phone_number_str, payment_wallet)
        return payment_wallet

    @classmethod
    def _create_payment_wallet(cls, full_name, phone_number_str='', phone_number=None, operator=None):
        registration_date = datetime.now()
        payment_wallet = PaymentWallet(
            RegistrationDate=registration_date,
            FullName=full_name,
            account_phone_number=phone_number_str if phone_number_str is not None else '',
            phone_number=phone_number,
            Type=PaymentWalletType.mobile_money,
            operator=operator if operator is not None else '',
        )
        return payment_wallet
