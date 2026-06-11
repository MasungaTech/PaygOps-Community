from datetime import datetime
import uuid
import requests
from pony.orm import db_session, select, rollback, flush
from payg_loan_system.payments.models.payment import Payment
from payg_loan_system.payments.models.wallet import PaymentWallet, PaymentWalletType
from payg_loan_system.payments.services.payment_creation_service import PaymentCreationService
from shared.logger.loggers import LogAPI, Error
from shared.services.base_service import BaseService
from shared.services.base_getter_service import BaseGetterService
from shared.services.settings_service import SettingsService
from shared.logger.loggers import AlreadyExistsError
from payg_loan_system.reversed_payments.services.service import PaymentReversalService
import config


class B2CPaymentService(BaseGetterService):

    @classmethod
    @db_session
    def _add_from_data_and_user(cls, payment_data, user, **kwargs):
        # Generate a unique transaction ID
        payment_uuid = payment_data.get('payment_uuid')
        payment = Payment.get(payment_uuid=payment_uuid)
        if payment:
            raise AlreadyExistsError(payment.get_serialized_object(alternate_model='b2c_payment'))
        
        # Create the payment in PaygOps
        payment = PaymentCreationService.create_payment(
            reference=payment_uuid,  # Initially use UUID as reference
            amount=-payment_data.get('amount'),
            sent_datetime=datetime.now(),
            phone_number=payment_data.get('wallet_msisdn'),
            memo=payment_data.get('memo'),
            wallet_operator=payment_data.get('wallet_operator'),
            country=payment_data.get('country'),
            currency=payment_data.get('currency'),
            payment_uuid=payment_uuid,
            full_name=payment_data.get('wallet_name', payment_data.get('wallet_msisdn'))
        )
        
        # Set initial status as pending
        payment.status = 'pending'
        
        # Make API call to gateway
        try:
            gateway_base_url = 'http://gateway:8002/api/v1'
            endpoint = f"{gateway_base_url}/b2c_payments"
            
            payload = {
                'payment_uuid': payment_uuid,
                'amount': float(payment.Amount),
                'recipient_msisdn': payment_data.get('wallet_msisdn'),
                'wallet_operator': payment.PaymentWallet.operator
            }
            
            if payment_data.get('memo'):
                payload['memo'] = payment_data.get('memo')
            if payment_data.get('remarks'):
                payload['remarks'] = payment_data.get('remarks')

            try:
                response = requests.post(endpoint, json=payload, timeout=60)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                LogAPI.Fatal(f'Failed to send payment request to gateway: {str(e)}')
                # Update payment status to failed
                gateway_data = {
                    'status': 'gateway_failure',
                    'transaction_id': payment_uuid
                }
                cls._edit_from_data_and_user(payment, gateway_data)
                raise Error('Failed to send payment request to gateway')
            
            LogAPI.Event(f'Payment request sent to gateway: {payment_uuid}')
            
        except requests.exceptions.RequestException as e:
            rollback()
            LogAPI.Fatal(f'Failed to send payment request to gateway: {str(e)}')
            raise Error('Failed to send payment request to gateway')
            #add logic for doing reversal incase of failure
        flush()
            
        return payment

    @classmethod
    @db_session
    def _edit_from_data_and_user(cls, payment, gateway_data, is_first_response=False, **kwargs):
        if not payment:
            raise Error(f'Payment not found for UUID: {payment.payment_uuid}')
            
        payment.Reference = gateway_data.get('transaction_id', payment.Reference)
        payment.status = gateway_data.get('status', payment.status)
        payment.PaymentReceptionTime = gateway_data.get('reception_datetime', payment.PaymentReceptionTime)
        payment.currency = gateway_data.get('currency', payment.currency)
        payment.country = gateway_data.get('country', payment.country)
        
        # Handle payment reversal if status is Failed
        if payment.status in config.B2C_FAILED_STATUSES:
            try:
                reversal_data = {
                    'manual_action': True,
                    'payment_transaction_id': payment.payment_uuid,
                    'wallet_operator': payment.wallet_operator
                }
                reversal, code = PaymentReversalService.process(reversal_data)
                if code != 201:
                    LogAPI.Fatal(f'Failed to process payment reversal for payment {payment.payment_uuid}. Status code: {code}')
                    raise Error(f'Failed to process payment reversal. Status code: {code}')
            except Exception as e:
                LogAPI.Fatal(f'Error processing payment reversal for payment {payment.payment_uuid}: {str(e)}')
                raise Error(f'Failed to process payment reversal: {str(e)}')
            
        return payment

    @classmethod
    @db_session
    def get_available_wallets(cls, client_id):
        wallets = PaymentWallet.select(
            lambda w: w.client.id == client_id and w.Type == PaymentWalletType.mobile_money
        )
            
        return wallets
    
    @classmethod
    @db_session
    def get_wallet_by_id(cls, wallet_id):
        wallet = PaymentWallet.get(
            lambda w: w.Type == PaymentWalletType.mobile_money and w.id == wallet_id
        )
        return wallet

    @classmethod
    @db_session
    def check_wallet_operator_status(cls, wallet_operator):
        """
        Check the status of a wallet operator against PaymentSendingGateways settings.
        
        Args:
            wallet_operator (str): The wallet operator to check (e.g. "Mpesa-KE")
            
        Returns:
            str: Status of the wallet operator - "active", "inactive", or "unavailable"
        """
        # Get the PaymentSendingGateways settings
        gateway_settings = SettingsService.get_setting('PaymentSendingGateways')
        
        # Capitalize the wallet operator for comparison
        wallet_operator = wallet_operator.lower() if wallet_operator else None
        
        if not wallet_operator:
            return "unavailable"
            
        # Check if the operator exists in settings
        if wallet_operator in gateway_settings:
            # Return status based on enabled flag
            return "active" if gateway_settings[wallet_operator]["enabled"] else "inactive"
            
        return "unavailable"
    
    @classmethod
    def get_filtered_objects(cls, user, **kwargs):
        b2c_payments = select(p for p in Payment if p.payment_uuid)
        return b2c_payments
    

    @classmethod
    @db_session
    def get_wallet_by_msisdn_and_operator(cls, msisdn, operator):
        wallet = PaymentWallet.get(
            lambda w: w.msisdn == msisdn and w.operator == operator
        )
        return wallet