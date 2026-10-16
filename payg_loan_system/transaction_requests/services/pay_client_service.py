from constants import MONEY_AMOUNT_PATTERN
from decimal import Decimal
from payg_loan_system.contracts.services.contract_getter_service import ContractGetterService
from payg_loan_system.actions.pay_client import handle_pay_client_request
from payg_loan_system.transaction_requests.services.transaction_service import BOOLEAN_SCHEMA, CONTRACT_REFERENCE_SCHEMA, LEAD_ID_SCHEMA, MOBILE_UUID_SCHEMA, TransactionService
from shared.logger.loggers import Error


class PayClientTransactionService(TransactionService):

    type = 'pay_client'
    permissions = ['PayClientActions']
    description = 'Allows paying a client that has an overpaid contract, the contract is given either by `contract_reference`, and then the `amount` is given. '
    schema = {
        "title": "By Contract Reference",
        "type": "object",
        "properties": {
            "contract_reference": CONTRACT_REFERENCE_SCHEMA,
            "contract_mobile_uuid": MOBILE_UUID_SCHEMA,
            "amount": {
                "default": "",
                "description": "The amount collected from the client/lead",
                "example": 12.34,
                "oneOf": [{
                    "type": "string",
                    "pattern": MONEY_AMOUNT_PATTERN
                }, {
                    "type": "number",
                    "format": "float"
                }]
            },
            "destination": {
                "description": "Where the payment to the client should go",
                "type": "string",
                "enum": ["cash_to_client", "cash_wallet", "mobile_money_account", "lead", "contract"],
                "example": "cash_wallet"
            },
            "wallet_id": {
                "description": "The ID of the mobile money wallet to use for the payment",
                "type": "integer",
                "example": 1234567890
            },
            "wallet_operator": {
                "description": "The operator of the mobile money wallet to use for the payment",
                "type": "string",
                "example": "Mpesa-KE"
            },
            "memo": {
                "description": "The memo of the payment",
                "type": "string",
                "example": "Payment for contract 1234567890"
            },
            "downpayment_lead_id": LEAD_ID_SCHEMA,
            "contract_to_pay_reference": CONTRACT_REFERENCE_SCHEMA,
            "send_sms_to_client": {
                **BOOLEAN_SCHEMA,
                **{'description': "Whether the result of the transaction should be sent to the client via SMS"}
            }
        },
        "required": ["contract_reference", "amount"]
    }
        

    @classmethod
    def _validate_data(cls, **kwargs):
        contract_reference = kwargs.get('contract_reference')
        contract_mobile_uuid = kwargs.get('contract_mobile_uuid')
        if contract_reference:
            contract = ContractGetterService.get_from_user_and_properties(kwargs['user'], reference=contract_reference, strict=True)
        elif contract_mobile_uuid:
            contract = ContractGetterService.get_from_user_and_properties(kwargs['user'], mobile_uuid=contract_mobile_uuid, strict=True)
        else:
            raise Error('NO_CONTRACT_PROVIDED')

        try:
            amount = Decimal(str(kwargs['amount']))
        except (KeyError, ValueError) as e:
            raise Error('INVALID_NUMBER_FORMAT') from e
        
        destination = kwargs.get('destination')
        if not destination:
            raise Error('Destination is required')
                
        return {'contract': contract, 'client': contract.client, 'amount': amount, 'destination': destination, 'wallet_id': kwargs.get('wallet_id', None), 'wallet_operator': kwargs.get('wallet_operator', None), 'memo': kwargs.get('memo', None), 'downpayment_lead_id': kwargs.get('downpayment_lead_id', None), 'contract_to_pay_reference': kwargs.get('contract_to_pay_reference', None)}

    @classmethod
    def _process(cls, user, offline, time, **kwargs):
        return handle_pay_client_request(
            acting_user=user,
            amount=kwargs['amount'],
            contract=kwargs['contract'],
            destination=kwargs['destination'],
            time=time,
            memo=kwargs.get('memo', None),
            wallet_id=kwargs.get('wallet_id', None),
            wallet_operator=kwargs.get('wallet_operator', None),
            downpayment_lead_id=kwargs.get('downpayment_lead_id', None),
            contract_to_pay_reference=kwargs.get('contract_to_pay_reference', None)
        )
