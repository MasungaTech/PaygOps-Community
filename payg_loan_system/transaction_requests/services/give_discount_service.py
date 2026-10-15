from payg_loan_system.transaction_requests.services.transaction_service import BOOLEAN_SCHEMA, CONTRACT_REFERENCE_SCHEMA, DEVICE_SERIAL_SCHEMA, NULLABLE_FLOAT, NULLABLE_STR, TransactionService
from payg_loan_system.actions.give_discount import give_discount
from shared.logger.loggers import Error


class GiveDiscountTransactionService(TransactionService):

    type = 'give_discount'
    permissions = ['GiveDiscountActions']
    description = 'Gives a discount to a contract given either by `device_serial` or `contract_reference`'
    schema = {
        "oneOf": [
            {
                "title": "By Device Serial Number",
                "type": "object",
                "properties": {
                    "device_serial": DEVICE_SERIAL_SCHEMA,
                    "discounted_days": {
                        "oneOf": NULLABLE_FLOAT,
                        "deprecated": True,
                        "example": 2,
                        "description": "See `discounted_units`"
                    },
                    "discounted_units": {
                        "oneOf": NULLABLE_FLOAT,
                        "example": 2,
                        "description": "Number of credit units (days if time) to be discounted"
                    },
                    "discounted_amount": {
                        "oneOf": NULLABLE_FLOAT,
                        "example": 10.34,
                        "description": "Amount to be discounted"
                    },
                    "note": {
                        "oneOf": NULLABLE_STR,
                        "example": "My note",
                        "description": "Note attached to the transaction with additional information about the discount"
                    },
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
                    "discounted_days": {
                        "oneOf": NULLABLE_FLOAT,
                        "deprecated": True,
                        "example": 2,
                        "description": "See `discounted_units`"
                    },
                    "discounted_units": {
                        "oneOf": NULLABLE_FLOAT,
                        "example": 2,
                        "description": "Number of credit units (days if time) to be discounted"
                    },
                    "discounted_amount": {
                        "oneOf": NULLABLE_FLOAT,
                        "example": 10.34,
                        "description": "Amount to be discounted"
                    },
                    "note": {
                        "oneOf": NULLABLE_STR,
                        "example": "My note",
                        "description": "Note attached to the transaction with additional information about the discount"
                    },
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
        
        units = kwargs.get('discounted_units') or kwargs.get('discounted_days')
        if (not units) and (not kwargs['discounted_amount']):
            raise Error('NEED_EITHER_DAYS_OR_AMOUNT')

        if units and kwargs['discounted_amount']:
            raise Error('Only days or amount can be provided, not both at the same time', code='NEED_ONLY_DAYS_OR_AMOUNT')

        return {'this_device': this_device, 'this_contract': this_contract, 'client': this_contract.client}

    @classmethod
    def _process(cls, user, offline, time, **kwargs):
        discounted_units = kwargs['discounted_units'] or kwargs.get('discounted_days')
        return give_discount(acting_user=user,
                             this_device=kwargs.get('this_device'),
                             this_contract=kwargs.get('this_contract'),
                             discounted_units=discounted_units,
                             discounted_amount=kwargs['discounted_amount'],
                             note=kwargs['note'])
