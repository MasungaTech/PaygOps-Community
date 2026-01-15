from payg_loan_system.transaction_requests.services.transaction_service import BOOLEAN_SCHEMA, CONTRACT_REFERENCE_SCHEMA, DEVICE_SERIAL_SCHEMA, REQUEST_CODE_SCHEMA, TransactionService, NOTES_SCHEMA
from payg_loan_system.contracts.services.contract_getter_service import ContractGetterService
from payg_loan_system.actions.undo_deregister import undo_deregister
from shared.logger.loggers import Error


class UndoDefaultTransactionService(TransactionService):

    type = 'undo_default'
    permissions = ['UndoContractDefaultedActions']
    description = 'Undoes the default of contract given either by `device_serial` or `contract_reference`'
    schema = {
        "properties": {
            "contract_reference": CONTRACT_REFERENCE_SCHEMA,
            "device_serial": DEVICE_SERIAL_SCHEMA,
            "request_code": REQUEST_CODE_SCHEMA,
            "send_sms_to_client": {
                **BOOLEAN_SCHEMA,
                **{'description': "Whether the result of the transaction should be sent to the client via SMS"}
            },
            "note": NOTES_SCHEMA
        },
        "required": ["contract_reference"]
    }

    @classmethod
    def _validate_data(cls, **kwargs):

        this_device = cls._get_device(kwargs['device_serial'], create=True)
        if kwargs['device_serial'] and not this_device:
            raise Error('A device could not be found with the serial number provided')

        this_contract = ContractGetterService.get_from_user_and_properties(kwargs['user'], reference=kwargs['contract_reference'], strict=True)

        return {'this_device': this_device, 'this_contract': this_contract, 'client': this_contract.client, 'note': kwargs.get('note')}

    @classmethod
    def _process(cls, user, offline, time, **kwargs):
        return undo_deregister(acting_user=user,
                               this_contract=kwargs['this_contract'] if kwargs.get('this_contract') else None,
                               this_device=kwargs['this_device'] if kwargs.get('this_device') else None,
                               registration_request_code=kwargs['request_code'],
                               note=kwargs.get('note'))
