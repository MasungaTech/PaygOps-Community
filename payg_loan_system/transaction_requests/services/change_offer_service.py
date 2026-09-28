from payg_loan_system.actions.change_offer import handle_offer_change_request
from payg_loan_system.transaction_requests.services.transaction_service import BOOLEAN_SCHEMA, CONTRACT_REFERENCE_SCHEMA, DEVICE_SERIAL_SCHEMA, TransactionService
from shared.logger.loggers import Error
from payg_loan_system.contracts.models.contract_model import ContractStatus
from constants import OPTIONAL_STRING_OPTIONS


class ChangeOfferTransactionService(TransactionService):

    type = 'change_offer'
    permissions = ['DoChangeOfferActions']
    description = 'Allows for changing a contract\'s offer. The contract is given either by `contract_reference` or `device_serial` and the new offer by its code with `new_offer_code`'
    schema = {
        "oneOf": [
            {
                "title": "By Device Serial Number",
                "type": "object",
                "properties": {
                    "device_serial": DEVICE_SERIAL_SCHEMA,
                    "new_offer_code": {
                        "type": "string",
                        "description": "The code of the new offer requested for the contract",
                        "example": "NEW_OFFER_CODE",
                    },
                    "note": {
                        "oneOf": OPTIONAL_STRING_OPTIONS,
                        "description": "A note to be added to the transaction",
                        "example": "Note to be added to the transaction"
                    },
                    "send_sms_to_client": {
                        **BOOLEAN_SCHEMA,
                        **{'description': "Whether the result of the transaction should be sent to the client via SMS"}
                    }
                },
                "required": ["device_serial", "new_offer_code"]
            },
            {
                "title": "By Contract Reference",
                "type": "object",
                "properties": {
                    "contract_reference": CONTRACT_REFERENCE_SCHEMA,
                    "new_offer_code": {
                        "type": "string",
                        "description": "The code of the new offer requested for the contract",
                        "example": "NEW_OFFER_CODE",
                    },
                    "note": {
                        "oneOf": OPTIONAL_STRING_OPTIONS,
                        "description": "A note to be added to the transaction",
                        "example": "Note to be added to the transaction"
                    },
                    "send_sms_to_client": {
                        **BOOLEAN_SCHEMA,
                        **{'description': "Whether the result of the transaction should be sent to the client via SMS"}
                    }
                },
                "required": ["contract_reference", "new_offer_code"]
            }
        ],
        "required": ["new_offer_code"]
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

        if contract.status == ContractStatus.paused:
            raise Error('CONTRACT_PAUSED')

        linked_device = contract.linked_device
        return {'contract': contract, 'this_device': linked_device, 'client': contract.client, 'note': kwargs.get('note')}

    @classmethod
    def _process(cls, user, offline, time, **kwargs):
        this_device = kwargs.get('this_device')
        return handle_offer_change_request(
            acting_user=user,
            registration_request_code=this_device.composed_serial if this_device else None,
            new_offer_code=kwargs['new_offer_code'],
            note=kwargs.get('note'),
            this_contract=kwargs['contract'],
            this_device=this_device
        )
