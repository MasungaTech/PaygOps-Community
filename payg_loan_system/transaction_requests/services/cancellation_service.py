from payg_loan_system.actions.deregister import handle_deregistration_request
from payg_loan_system.contracts.models.addons_model import AddOnType
from payg_loan_system.contracts.models.contract_status import ContractStatus
from payg_loan_system.contracts.models.reconciled_payment_type import ReconciledPaymentType
from payg_loan_system.contracts.services.addon_service import AddonService
from payg_loan_system.contracts.services.contract_repayment_service import \
    ContractRepaymentService, ContractRepaymentDiscountTypes
from payg_loan_system.contracts.services.reconciled_payment_service import ReconciledPaymentService
from payg_loan_system.transaction_requests.services.transaction_service import (
    BOOLEAN_SCHEMA, CONTRACT_REFERENCE_SCHEMA, DEVICE_SERIAL_SCHEMA, NOTES_SCHEMA,
    REQUEST_CODE_SCHEMA, TransactionService)
from shared.helpers.form_helpers import value_to_bool
from shared.logger.loggers import Error
from constants import OPTIONAL_STRING_OPTIONS


class CancelContractTransactionService(TransactionService):

    type = 'cancel'
    permissions = ['CancelContractActions']
    description = 'Cancels a contract given either by `device_serial` or `contract_reference`'
    schema = {
        "oneOf": [
                {
                    "title": "By Device Serial Number",
                    "type": "object",
                    "properties": {
                        "device_serial": DEVICE_SERIAL_SCHEMA,
                        "request_code": REQUEST_CODE_SCHEMA,
                        "duplicate_lead": {
                            **BOOLEAN_SCHEMA, 
                            **{'description': "Whether the lead associated with this contract should be duplicated or not (useful when the lead was registered by mistake)"}
                        },
                        "send_sms": {
                            **BOOLEAN_SCHEMA,
                            **{'description': "Whether the result of the transaction should be sent to the client to inform about the cancellation of the contract"}
                        },
                        "note": NOTES_SCHEMA
                    },
                    "required": ["device_serial"]
                },
                {
                    "title": "By Contract Reference",
                    "type": "object",
                    "properties": {
                        "contract_reference": CONTRACT_REFERENCE_SCHEMA,
                        "request_code": REQUEST_CODE_SCHEMA,
                        "duplicate_lead": {
                            **BOOLEAN_SCHEMA, 
                            **{'description': "Whether the lead associated with this contract should be duplicated or not (useful when the lead was registered by mistake)"}
                        },
                        "send_sms": {
                            **BOOLEAN_SCHEMA,
                            **{'description': "Whether the result of the transaction should be sent to the client to inform about the cancellation of the contract"}
                        },
                        "note": NOTES_SCHEMA
                    },
                    "required": ["contract_reference"]
                },
            ],

    }


    @classmethod
    def _validate_data(cls, **kwargs):
        contract = cls._get_contract(
            device_serial=kwargs.get('device_serial'),
            contract_reference=kwargs.get('contract_reference'),
            user=kwargs['user']
        )
        if not contract:
            raise Error('INVALID_CONTRACT')
        if contract.status == ContractStatus.cancelled:
            raise Error('Contract already cancelled')
        linked_device = contract.linked_device
        if not linked_device:
            raise Error('CONTRACT_HAS_NO_DEVICE')
        if contract.status == ContractStatus.paused:
            raise Error('CONTRACT_PAUSED')
        return {'contract': contract, 'this_device': linked_device, 'client': contract.client, 'note': kwargs.get('note')}

    @classmethod
    def _process(cls, user, offline, time, contract, this_device,**kwargs):

        # Needed to compile the info of the money to be reconciled to the client
        payment_recons = {}
        wallet_recons = {}
        def add_or_set(d, k, v):
            if k in d: d[k] += v
            else: d[k] = v
        def account_reconciled(reconciled):
            if reconciled.linked_payment: add_or_set(payment_recons, reconciled.linked_payment, reconciled.amount)
            else: add_or_set(wallet_recons, reconciled.payment_account, reconciled.amount)
        
        # We first need to create discounts opposite to the existing ones
        # to avoid remaining amount on the contract or negative amount if negative discounts
        for repayment in contract.repayments.filter(lambda r: not r.converse and r.discount_type == ContractRepaymentDiscountTypes.manual_discount):
            ContractRepaymentService.give_amount_discount(contract, -repayment.amount, note='Cancelling manual discounts before contract cancellation.')
        for repayment in contract.repayments.filter(lambda r: r.reversable):
            ContractRepaymentService.reverse_repayment(repayment, user, force_allow_below_downpayment=True, cancelling=True)
            for reconciled in repayment.reconciled_payments: account_reconciled(reconciled)
        sorter = lambda a: a.offer_version.offer.type == AddOnType.deposit_change and a.offer_version.downpayment < 0
        for addon in contract.add_ons.filter(lambda a: bool(a.already_paid)).order_by(sorter):
            for reconciled in addon.reconciled_payments.select(lambda r: not r.converse):
                ReconciledPaymentService.revert(reconciled, time=time)
                account_reconciled(reconciled)
        
        for addon in contract.add_ons:
            AddonService.set_delivery_status(addon, user, delivered=False, cancelling=True)

        for payment, total_to_reconcile in payment_recons.items():
            ReconciledPaymentService.create_reconciliation(
                person=contract.client.person,
                type=ReconciledPaymentType.payment_pending_reconciliation,
                payment=payment,
                amount=total_to_reconcile,
                account=payment.PaymentWallet
            )
        for wallet, total_to_reconcile in wallet_recons.items():
            ReconciledPaymentService.create_reconciliation(
                person=reconciled.get_person(),
                type=ReconciledPaymentType.payment_pending_reconciliation,
                amount=total_to_reconcile,
                account=wallet
            )

        duplicate_lead = value_to_bool(kwargs.get('duplicate_lead', False))
        send_sms = value_to_bool(kwargs.get('send_sms', False))
        return handle_deregistration_request(
            user, this_device, registration_request_code=kwargs['request_code'],
            cancel_contract=True, duplicate_lead=duplicate_lead, send_sms=send_sms, note=kwargs.get('note')
        )
