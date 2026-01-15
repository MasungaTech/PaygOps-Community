from payg_loan_system.transaction_requests.services.transaction_service import BOOLEAN_SCHEMA, CONTRACT_ADDON_REFERENCE_SCHEMA, CONTRACT_REFERENCE_SCHEMA, DEVICE_SERIAL_SCHEMA, REQUEST_CODE_SCHEMA, TransactionService
from payg_loan_system.actions.swap_device import handle_device_change_request
from constants import OPTIONAL_STRING_OPTIONS
from shared.logger.loggers import Error


class SwapDeviceTransactionService(TransactionService):

    type = 'swap_device'
    permissions = ['SwapDeviceActions']
    description = 'Swaps the devices of a contract given by either `old_device_serial` or `contract_reference` with the `new_device_serial`'
    schema = {
        "oneOf": [
            {
                "title": "By Device Serial Number",
                "type": "object",
                "properties": {
                    "old_device_serial": DEVICE_SERIAL_SCHEMA,
                    "new_device_serial": DEVICE_SERIAL_SCHEMA,
                    "new_request_code": REQUEST_CODE_SCHEMA,
                    "old_request_code": REQUEST_CODE_SCHEMA,
                    "send_sms_to_client": {
                        **BOOLEAN_SCHEMA,
                        **{'description': "Whether the result of the transaction should be sent to the client via SMS"}
                    },
                    "note": {
                        "oneOf": OPTIONAL_STRING_OPTIONS,
                        "description": "A note to be added to the transaction",
                        "example": "Note to be added to the transaction"
                    }
                },
                "required": ["old_device_serial", "new_device_serial"]
            },
            {
                "title": "By Contract Reference",
                "type": "object",
                "properties": {
                    "contract_reference": CONTRACT_REFERENCE_SCHEMA,
                    "new_device_serial": DEVICE_SERIAL_SCHEMA,
                    "new_request_code": REQUEST_CODE_SCHEMA,
                    "old_request_code": REQUEST_CODE_SCHEMA,
                    "send_sms_to_client": {
                        **BOOLEAN_SCHEMA,
                        **{'description': "Whether the result of the transaction should be sent to the client via SMS"}
                    },
                    "note": {
                        "oneOf": OPTIONAL_STRING_OPTIONS,
                        "description": "A note to be added to the transaction",
                        "example": "Note to be added to the transaction"
                    }
                },
                "required": ["contract_reference", "new_device_serial"]
            },
            {
                "title": "By Contract Addons Reference",
                "type": "object",
                "properties": {
                    "contract_addon_reference": CONTRACT_ADDON_REFERENCE_SCHEMA,
                    "new_device_serial": DEVICE_SERIAL_SCHEMA,
                    "new_request_code": REQUEST_CODE_SCHEMA,
                    "old_request_code": REQUEST_CODE_SCHEMA,
                    "send_sms_to_client": {
                        **BOOLEAN_SCHEMA,
                        **{'description': "Whether the result of the transaction should be sent to the client via SMS"}
                    },
                    "note": {
                        "oneOf": OPTIONAL_STRING_OPTIONS,
                        "description": "A note to be added to the transaction",
                        "example": "Note to be added to the transaction"
                    }
                },
                "required": ["contract_addon_reference", "new_device_serial"]
            }
        ]
    }

    @classmethod
    def _validate_data(cls, **kwargs):

        contract_addon = kwargs.get('contract_addon_reference', None)
        contract = None

        if contract_addon:
            contract_addon = cls._get_contract_addon(contract_addon, kwargs['user'])
            if not contract_addon:
                raise Error('INVALID_CONTRACT_ADDON')
            contract = contract_addon.contract
        else:

            contract = cls._get_contract(
                kwargs.get('old_device_serial'),
                kwargs.get('contract_reference'),
                kwargs['user']
            )
            contract_addon = None

            if not contract:
                if kwargs.get('old_device_serial'):
                    raise Error('DEVICE_NOT_REGISTERED')
                raise Error('INVALID_CONTRACT')

            if not contract.linked_device:
                raise Error('CONTRACT_HAS_NO_DEVICE')

        new_device = cls._get_device(kwargs['new_device_serial'], create=True)
        if not new_device:
            raise Error('A device could not be found with the new serial number provided')

        return {'new_device': new_device, 'client': contract.client, 'contract': contract, 'contract_addon':contract_addon, 'note': kwargs.get('note')}

    @classmethod
    def _process(cls, user, offline, time, **kwargs):
        return handle_device_change_request(
            acting_user=user,
            contract=kwargs['contract'],
            new_device=kwargs['new_device'],
            registration_request_code_old=kwargs['old_request_code'],
            registration_request_code_new=kwargs['new_request_code'],
            contract_addon=kwargs["contract_addon"],
            note=kwargs.get('note')
        )
