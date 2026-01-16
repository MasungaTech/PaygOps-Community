from payg_loan_system.transaction_requests.services.transaction_service import (
    BOOLEAN_SCHEMA, CONTRACT_ADDON_REFERENCE_SCHEMA, DEVICE_SERIAL_SCHEMA, TransactionService
)
from payg_loan_system.actions.assign_device import handle_device_assignment_request
from shared.logger.loggers import Error


class AssignDeviceTransactionService(TransactionService):

    type = 'assign_device'
    permissions = ['SwapDeviceActions']
    description = 'Assigns a device to a contract addon'
    schema = {
        "type": "object",
        "properties": {
            "contract_addon_reference": CONTRACT_ADDON_REFERENCE_SCHEMA,
            "new_device_serial": DEVICE_SERIAL_SCHEMA,
            "send_sms_to_client": {
                        **BOOLEAN_SCHEMA,
                        **{'description': "Whether the result of the transaction should be sent to the client via SMS"}
            }
        },
        "required": ["contract_addon_reference", "new_device_serial"]
    }

    @classmethod
    def _validate_data(cls, **kwargs):
        contract_addon = cls._get_contract_addon(kwargs['contract_addon_reference'], kwargs['user'])
        if not contract_addon:
            raise Error('INVALID_CONTRACT_ADDON')
            
        contract = contract_addon.contract
        if not contract:
            raise Error('CONTRACT_ADDON_HAS_NO_CONTRACT')

        new_device = cls._get_device(kwargs['new_device_serial'], create=True)
        if not new_device:
            raise Error('A device could not be found with the new serial number provided')

        return {
            'new_device': new_device,
            'contract': contract,
            'contract_addon': contract_addon,
            'client': contract.client,
        }

    @classmethod
    def _process(cls, user, offline, time, **kwargs):
        return handle_device_assignment_request(
            acting_user=user,
            contract=kwargs['contract'],
            new_device=kwargs['new_device'],
            contract_addon=kwargs['contract_addon']
        )