from pony.orm.core import desc
from payg_loan_system.transaction_requests.services.transaction_service import BOOLEAN_SCHEMA, CONTRACT_REFERENCE_SCHEMA, DEVICE_SERIAL_SCHEMA, REQUEST_CODE_SCHEMA, TransactionService
from payg_loan_system.actions.activation import sync_activation
from shared.logger.loggers import Error
from payg_loan_system.contracts.models.contract_status import ContractStatus


class SyncActivationTransactionService(TransactionService):

    type = 'sync_activation'
    permissions = ['SyncActivationActions']
    description = 'Activates the linked device of a contract given by either `device_serial` or `contract_reference`'
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

        contract = cls._get_contract(
            kwargs.get('device_serial'),
            kwargs.get('contract_reference'),
            kwargs['user']
        )
        if not contract:
            raise Error('Contract not found')
        if not contract.linked_device:
            raise Error('Contract does not have a device to activate')
        if contract.status == ContractStatus.paused:
            raise Error('CONTRACT_PAUSED')

        return {'contract': contract, 'this_device': contract.linked_device, 'client': contract.client}

    @classmethod
    def _process(cls, user, offline, time, **kwargs):
        return [sync_activation(kwargs['contract'], activation_request_code=kwargs['request_code'], allow_negative=True)]
