from payg_loan_system.contracts.models.contract_event_model import ContractEventType
from payg_loan_system.contracts.services.contract_cache_service import ContractCacheService
from payg_loan_system.transaction_requests.services.transaction_service import CONTRACT_REFERENCE_SCHEMA, DEVICE_SERIAL_SCHEMA, TransactionService, NOTES_SCHEMA
from shared.logger.loggers import Error
from constants import MONEY_REQUIRED_OPTIONS
from decimal import Decimal
from payg_loan_system.contracts.models.contract_model import ContractStatus


class ExpectedPaidChangeTransactionService(TransactionService):

    type = 'expected_paid_change'
    permissions = ['ChangeExpectedPaidActions']
    description = 'Modifies a contract expected paid amount given either by `device_serial` or `contract_reference` and `adjustment_amount`'
    schema = {
        "oneOf": [
            {
                "title": "By Device Serial Number",
                "type": "object",
                "properties": {
                    "device_serial": DEVICE_SERIAL_SCHEMA,
                    "adjustment_amount": {
                        "oneOf": MONEY_REQUIRED_OPTIONS,
                        "description": "The amount to be adjusted",
                        "example": "NPG-12345"
                    },
                    "note": NOTES_SCHEMA
                },
                "required": ["device_serial", "adjustment_amount"]
            },
            {
                "title": "By Contract Reference",
                "type": "object",
                "properties": {
                    "contract_reference": CONTRACT_REFERENCE_SCHEMA,
                    "adjustment_amount": {
                        "oneOf": MONEY_REQUIRED_OPTIONS,
                        "description": "The amount to be adjusted",
                        "example": "NPG-12345"
                    },
                    "note": NOTES_SCHEMA
                },
                "required": ["contract_reference", "adjustment_amount"]
            }
        ]
    }

    @classmethod
    def _validate_data(cls, **kwargs):
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
        processed['client'] = contract.client
        if contract.offer.is_lump_sum:
            raise Error('EXPECTED_PAID_NOT_POSSIBLE_LUMP_SUM')
        if contract.can_be_completed and contract.get_expected_amount_repaid() + Decimal(str(kwargs['adjustment_amount'])) > contract.get_total_value():
            raise Error('EXPECTED_PAID_CANNOT_BE_MORE_THAN_TOTAL_VALUE', maximum=contract.get_total_value()-contract.get_expected_amount_repaid())
        if contract.status == ContractStatus.paused:
            raise Error('CONTRACT_PAUSED')
        return processed

    @classmethod
    def _process(cls, user, offline, time, **kwargs):
        device = kwargs['this_device']
        contract = device.contract
        client = contract.client
        adjustment_amount = Decimal(str(kwargs['adjustment_amount']))
        note = kwargs.get('note') if kwargs.get('note') else ''
        contract.contract_events.create(
            type=ContractEventType.expected_paid_change,
            time=time,
            approver=user,
            added_amount=adjustment_amount,
            note=note
        )
        ContractCacheService.update_expected_paid(contract, force=True)
        progression = contract.get_weeks_progression_dict()
        return [{
            "success": True,
            "status": "EXPECTED_PAID_CHANGE_SUCCESS",
            'client_id': client.id,
            'name': client.person.name,
            'surname': client.person.surname,
            'contract_reference': contract.reference,
            "adjustment_amount": adjustment_amount,
            "expected_paid_amount": contract.get_expected_amount_repaid(),
        }] + ([{
            "success": True,
            "status": "PROGRESSION_USER",
            'weeks_paid': progression['weeks_paid'],
            'days_paid': progression['days_paid'],
            'weeks_to_pay': progression['weeks_to_pay'],
            'days_to_pay': progression['days_to_pay'],
            'remaining_weeks_to_pay': progression['remaining_weeks_to_pay'],
            'remaining_days_to_pay': progression['remaining_days_to_pay']
        }] if progression else [])
