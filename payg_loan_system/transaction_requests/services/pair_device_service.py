from payg_loan_system.transaction_requests.services.transaction_service import BOOLEAN_SCHEMA, CONTRACT_REFERENCE_SCHEMA, DEVICE_SERIAL_SCHEMA, REQUEST_CODE_SCHEMA, TransactionService
from payg_loan_system.actions.activation import pair_device
from shared.logger.loggers import Error
from payg_loan_system.contracts.models.contract_status import ContractStatus


class PairDeviceTransactionService(TransactionService):

    type = 'pair_device'
    permissions = ['PairDevices']
    description = 'Pairs a device linked to a contract given by either `device_serial` or `contract_reference`'
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
                    }
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
                    }
                },
                "required": ["contract_reference"]
            }
        ]
    }

    @classmethod
    def _validate_data(cls, **kwargs):

        this_device = cls._get_device(
            kwargs.get('device_serial'),
            kwargs.get('contract_reference'),
            kwargs['user']
        )
        if not this_device:
            raise Error('Device not found')

        return {'this_device': this_device, 'client': this_device.contract.client}

    @classmethod
    def _process(cls, user, offline, time, **kwargs):
        return [pair_device(kwargs['this_device'], activation_request_code=kwargs['request_code'])]

