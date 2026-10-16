from constants import DELAY_DAYS_AMOUNT_PATTERN, OPTIONAL_DATETIME_OPTIONS
from payg_loan_system.transaction_requests.services.transaction_service import BOOLEAN_SCHEMA, CONTRACT_REFERENCE_SCHEMA, DEVICE_SERIAL_SCHEMA, NULLABLE_STR, TransactionService
from payg_loan_system.actions.give_delay import handle_give_delay_request
from shared.logger.loggers import Error


class GiveDelayTransactionService(TransactionService):

    type = 'give_delay'
    permissions = ['GiveDelayActions']
    description = 'Gives a delay to a contract given either by `device_serial` or `contract_reference`'
    schema = {
        "oneOf": [
            {
                "title": "By Device Serial Number and delayed_days",
                "type": "object",
                "properties": {
                    "device_serial": DEVICE_SERIAL_SCHEMA,
                    "delayed_days": {
                        "default": "",
                        "description": "The number of days to be delayed",
                        "example": 2,
                        "oneOf": [{
                            "type": "string",
                            "pattern": DELAY_DAYS_AMOUNT_PATTERN
                        }, {
                            "type": "number",
                            "format": "float"
                        }
                        ]
                    },
                    "note": {
                        "oneOf": NULLABLE_STR,
                        "description": "Note attached to the delay with additional information",
                        "example": "My note"
                    },
                    "send_sms_to_client": {
                        **BOOLEAN_SCHEMA,
                        **{'description': "Whether the result of the transaction should be sent to the client via SMS"}
                    }
                },
                "required": ["device_serial", "delayed_days"],
            },
            {
             "title": "By Device Serial Number and delayed_date",
                "type": "object",
                "properties": {
                    "device_serial": DEVICE_SERIAL_SCHEMA,
                    "delayed_date":{
                        "default": "",
                        "description": "The date to be delayed",
                        "example": "2024-08-06",
                        "oneOf": OPTIONAL_DATETIME_OPTIONS
                    },
                    "note": {
                        "oneOf": NULLABLE_STR,
                        "description": "Note attached to the delay with additional information",
                        "example": "My note"
                    },
                    "send_sms_to_client": {
                        **BOOLEAN_SCHEMA,
                        **{'description': "Whether the result of the transaction should be sent to the client via SMS"}
                    }
                },
                "required": ["device_serial", "delayed_date"],
            },
            {
                "title": "By Contract Reference and delayed_days",
                "type": "object",
                "properties": {
                    "delayed_days": {
                        "default": "",
                        "description": "The number of days to be delayed",
                        "example": 2,
                        "oneOf": [{
                            "type": "string",
                            "pattern": DELAY_DAYS_AMOUNT_PATTERN
                        }, {
                            "type": "number",
                            "format": "float"
                        },
                        ]
                    },
                    "contract_reference": CONTRACT_REFERENCE_SCHEMA,
                    "note": {
                        "oneOf": NULLABLE_STR,
                        "description": "Note attached to the delay with additional information",
                        "example": "My note"
                    },
                    "send_sms_to_client": {
                        **BOOLEAN_SCHEMA,
                        **{'description': "Whether the result of the transaction should be sent to the client via SMS"}
                    }
                },
                "required": ["contract_reference", "delayed_days"],
            },
            {
                "title": "By Contract Reference and delayed_date",
                "type": "object",
                "properties": {
                    "delayed_date":{
                        "default": "",
                        "description": "The date  to be delayed",
                        "example": "2024-08-06",
                        "oneOf": OPTIONAL_DATETIME_OPTIONS
                    },
                    "contract_reference": CONTRACT_REFERENCE_SCHEMA,
                    "note": {
                        "oneOf": NULLABLE_STR,
                        "description": "Note attached to the delay with additional information",
                        "example": "My note"
                    },
                    "send_sms_to_client": {
                        **BOOLEAN_SCHEMA,
                        **{'description': "Whether the result of the transaction should be sent to the client via SMS"}
                    }
                },
                "required": ["contract_reference", "delayed_date"],
            }
        ]
    }
    

    @classmethod
    def _validate_data(cls, **kwargs):

        this_device = None
        this_contract = None
        
        if kwargs.get('device_serial'):
            this_device = cls._get_device(
                kwargs.get('device_serial'),
                None,
                kwargs['user']
            )
            if not this_device:
                raise Error('A contract could not be found with the serial number or reference provided')
            this_contract = this_device.contract
        elif kwargs.get('contract_reference'):
            this_contract = cls._get_contract(
                None,
                kwargs.get('contract_reference'),
                kwargs['user']
            )
            if not this_contract:
                raise Error('A contract could not be found with the serial number or reference provided')
            this_device = this_contract.linked_device
        else:
            raise Error('A contract could not be found with the serial number or reference provided')

        if not this_contract:
            raise Error('DEVICE_NOT_REGISTERED')

        return {'this_device': this_device, 'this_contract': this_contract, 'client': this_contract.client}

    @classmethod
    def _process(cls, user, offline, time, **kwargs):
        return handle_give_delay_request(user, this_client=kwargs.get('client'),
                                         this_device=kwargs.get('this_device'),
                                         this_contract=kwargs.get('this_contract'),
                                         delayed_days=kwargs.get('delayed_days'),
                                         note=kwargs.get('note'),
                                         delayed_date=kwargs.get('delayed_date'))
