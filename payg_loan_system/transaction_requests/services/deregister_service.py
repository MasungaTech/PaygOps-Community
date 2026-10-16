from payg_loan_system.actions.deregister import handle_deregistration_request
from payg_loan_system.transaction_requests.services.transaction_service import BOOLEAN_SCHEMA, CONTRACT_REFERENCE_SCHEMA, DEVICE_SERIAL_SCHEMA, REQUEST_CODE_SCHEMA, TransactionService, NOTES_SCHEMA
from shared.logger.loggers import Error
from payg_loan_system.contracts.models.contract_model import ContractStatus



class DeRegisterTransactionService(TransactionService):

    type = 'deregister'
    permissions = ['DeRegisterActions']
    description = 'Deregister a contract given either by `device_serial` or `contract_reference`'
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
        processed = {'this_device': cls._get_device(
            kwargs.get('device_serial'),
            kwargs.get('contract_reference'),
            kwargs['user'],
            )}
        if not processed['this_device']:
            raise Error('A contract could not be found with the serial number or reference provided')
        contract = getattr(processed['this_device'], 'contract', None)
        if not contract:
            raise Error('DEVICE_NOT_REGISTERED')
        if contract.status == ContractStatus.paused:
            raise Error('CONTRACT_PAUSED')
        processed['client'] = getattr(contract, 'client', None)
        return processed

    @classmethod
    def _process(cls, user, offline, time, **kwargs):
        return handle_deregistration_request(user, kwargs['this_device'],
                                             registration_request_code=kwargs['request_code'], note=kwargs.get('note'))
