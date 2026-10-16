from payg_loan_system.actions.default import handle_default_request
from payg_loan_system.transaction_requests.services.transaction_service import BOOLEAN_SCHEMA, CONTRACT_REFERENCE_SCHEMA, DEVICE_SERIAL_SCHEMA, REQUEST_CODE_SCHEMA, TransactionService, NOTES_SCHEMA
from shared.logger.loggers import Error
from payg_loan_system.contracts.models.contract_model import ContractStatus
from shared.services.settings_service import SettingsService


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
        contract = None
        if not SettingsService.get_setting('ContractDeviceRestrictions') == 'no_device' and not kwargs.get('device_serial'):
            processed = {'this_contract': cls._get_contract(
                contract_reference=kwargs.get('contract_reference'),
                user=kwargs['user']
            )}
            if not processed['this_contract']:
                raise Error('A contract could not be found with the reference provided')
            contract = processed['this_contract']
        elif not SettingsService.get_setting('ContractDeviceRestrictions') == 'no_device' and kwargs.get('device_serial'):
            processed = {'this_device': cls._get_device(
                kwargs.get('device_serial'),
                kwargs.get('contract_reference'),
                kwargs['user']
            )}
            if not processed['this_device']:
                raise Error('A contract could not be found with the serial number or reference provided')
            contract = processed['this_device'].contract
        if not contract:
            raise Error('DEVICE_NOT_REGISTERED')
        if contract.status == ContractStatus.paused:
            raise Error('CONTRACT_PAUSED')
        processed['client'] = contract.client
        return processed

    @classmethod
    def _process(cls, user, offline, time, **kwargs):
        return handle_default_request(
            user,
            this_device=kwargs['this_device'] if kwargs.get('this_device') else None,
            this_contract=kwargs['this_contract'] if kwargs.get('this_contract') else None,
            registration_request_code=kwargs['request_code'],
            note=kwargs.get('note')
        )
