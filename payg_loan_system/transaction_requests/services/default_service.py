from payg_loan_system.actions.default import handle_default_request
from payg_loan_system.transaction_requests.services.transaction_service import BOOLEAN_SCHEMA, CONTRACT_REFERENCE_SCHEMA, DEVICE_SERIAL_SCHEMA, REQUEST_CODE_SCHEMA, TransactionService, NOTES_SCHEMA
from shared.logger.loggers import Error
from payg_loan_system.contracts.models.contract_model import ContractStatus


class DefaultTransactionService(TransactionService):

    type = 'default'
    permissions = ['MarkContractDefaultedActions']
    description = 'Defaults a contract given either by `device_serial` or `contract_reference`'
    schema = {
        "oneOf": [
            {
                "title": "By Device Serial Number",
                "type": "object",
                "properties": {
                    "device_serial": DEVICE_SERIAL_SCHEMA,
                    "request_code": REQUEST_CODE_SCHEMA,
                    "send_sms_to_client": {
                        **BOOLEAN_SCHEMA,
                        **{'description': "Whether the result of the transaction should be sent to the client via SMS"}
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
                    "send_sms_to_client": {
                        **BOOLEAN_SCHEMA,
                        **{'description': "Whether the result of the transaction should be sent to the client via SMS"}
                    },
                    "note": NOTES_SCHEMA
                },
                "required": ["contract_reference"]
            }
        ]
    }

    @classmethod
    def _validate_data(cls, **kwargs):
        user = kwargs['user']
        device_serial = kwargs.get('device_serial')
        contract_reference = kwargs.get('contract_reference')
        this_device = None
        this_contract = None

        if device_serial:
            this_device = cls._get_device(device_serial, contract_reference, user)
            if not this_device:
                raise Error('A contract could not be found with the serial number or reference provided')
            this_contract = this_device.contract
            if not this_contract:
                raise Error('DEVICE_NOT_REGISTERED')
        elif contract_reference:
            this_contract = cls._get_contract(contract_reference=contract_reference, user=user)
            if not this_contract:
                raise Error('A contract could not be found with the reference provided')
            this_device = this_contract.linked_device
        else:
            raise Error('DEVICE_NOT_REGISTERED')

        if this_contract.status == ContractStatus.paused:
            raise Error('CONTRACT_PAUSED')
        return {
            'this_device': this_device,
            'this_contract': this_contract,
            'client': this_contract.client,
        }

    @classmethod
    def _process(cls, user, offline, time, **kwargs):
        return handle_default_request(
            user,
            this_device=kwargs['this_device'] if kwargs.get('this_device') else None,
            this_contract=kwargs['this_contract'] if kwargs.get('this_contract') else None,
            registration_request_code=kwargs['request_code'],
            note=kwargs.get('note')
        )
