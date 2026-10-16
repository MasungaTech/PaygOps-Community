from payg_loan_system.contracts.services.addon_list_service import AddonListService
from constants import MONEY_AMOUNT_PATTERN
from decimal import Decimal
from payg_loan_system.contracts.models.contract_model import ContractStatus
from payg_loan_system.contracts.services.addon_service import AddonService
from payg_loan_system.contracts.services.contract_getter_service import ContractGetterService
from sales_system.leads.models.lead import Lead
from payg_loan_system.actions.collect_cash import collect_cash, handle_paycash_request
from payg_loan_system.payments.services.payment_processor_service import PaymentProcessorService
from sales_system.leads.services.edit_lead_service import EditLeadService
from payg_loan_system.transaction_requests.services.transaction_service import BOOLEAN_SCHEMA, CONTRACT_REFERENCE_SCHEMA, DEVICE_SERIAL_SCHEMA, LEAD_ID_SCHEMA, MOBILE_UUID_SCHEMA, TransactionService, NOTES_SCHEMA
from sales_system.leads.services.lead_getter_service import LeadGetterService
from shared.logger.loggers import Error


class CollectCashTransactionService(TransactionService):

    type = 'collect_cash'
    permissions = ['CollectCashActions']
    description = 'Allows for collecting cash from a client with a contract or from a lead. If from a client' + \
    ', the contract is given either by `contract_reference` or `device_serial` and if for a lead, using `lead_id`' + \
    '. The `amount` can be reconciled to the contract or to an add-on, if `addon_reference` specified'
    schema = {
        "oneOf": [
            {
                "title": "By Device Serial Number",
                "type": "object",
                "properties": {
                    "device_serial": DEVICE_SERIAL_SCHEMA,
                    "amount": {
                        "default": "",
                        "description": "The amount collected from the client/lead",
                        "example": 12.34,
                        "oneOf": [{
                            "type": "string",
                            "pattern": MONEY_AMOUNT_PATTERN
                        }, {
                            "type": "number",
                            "format": "float"
                        }]
                    },
                    "note": NOTES_SCHEMA,
                    "contract_mobile_uuid": MOBILE_UUID_SCHEMA,
                    "send_sms_to_client": {
                        **BOOLEAN_SCHEMA,
                        **{'description': "Whether the result of the transaction should be sent to the client via SMS"}
                    }
                },
                "required": ["device_serial", "amount"]
            },
            {
                "title": "By Contract Reference",
                "type": "object",
                "properties": {
                    "contract_reference": CONTRACT_REFERENCE_SCHEMA,
                    "amount": {
                        "default": "",
                        "description": "The amount collected from the client/lead",
                        "example": 12.34,
                        "oneOf": [{
                            "type": "string",
                            "pattern": MONEY_AMOUNT_PATTERN
                        }, {
                            "type": "number",
                            "format": "float"
                        }]
                    },
                    "note": NOTES_SCHEMA,
                    "contract_mobile_uuid": MOBILE_UUID_SCHEMA,
                    "send_sms_to_client": {
                        **BOOLEAN_SCHEMA,
                        **{'description': "Whether the result of the transaction should be sent to the client via SMS"}
                    }
                },
                "required": ["contract_reference", "amount"]
            },
            {
                "title": "By Lead Id",
                "type": "object",
                "properties": {
                    "lead_id": LEAD_ID_SCHEMA,
                    "amount": {
                        "default": "",
                        "description": "The amount collected from the client/lead",
                        "example": 12.34,
                        "oneOf": [{
                            "type": "string",
                            "pattern": MONEY_AMOUNT_PATTERN
                        }, {
                            "type": "number",
                            "format": "float"
                        }]
                    },
                    "note": NOTES_SCHEMA,
                    "send_sms_to_client": {
                        **BOOLEAN_SCHEMA,
                        **{'description': "Whether the result of the transaction should be sent to the client via SMS"}
                    }
                },
                "required": ["lead_id", "amount"]
            },
            {
                "title": "By Add-on Reference",
                "type": "object",
                "properties": {
                    "addon_reference": {
                        "default": "",
                        "description": "The reference of the add-on to which the amount is goint to be reconciled",
                        "example": "C0103043-A3",
                        "type": "string"
                    },
                    "note": {
                        "description": "Notes about the collection",
                        "example": "Notes about the collection",
                        "type": "string",
                        "maxLength": 40
                    },
                    "send_sms_to_client": {
                        **BOOLEAN_SCHEMA,
                        **{'description': "Whether the result of the transaction should be sent to the client via SMS"}
                    }
                },
                "required": ["addon_reference"]
            }
        ]
    }

    @classmethod
    def _validate_data(cls, **kwargs):
        contract_reference = kwargs.get('contract_reference')
        contract_mobile_uuid = kwargs.get('contract_mobile_uuid')
        this_contract = None
        if not contract_reference and contract_mobile_uuid:
            this_contract = ContractGetterService.get_from_user_and_properties(kwargs['user'], mobile_uuid=contract_mobile_uuid, strict=True)
            contract_reference = this_contract.reference
        elif contract_reference:
            this_contract = cls._get_contract(contract_reference=contract_reference, user=kwargs['user'])
        this_device = cls._get_device(
            device_serial=kwargs.get('device_serial'),
            contract_reference=contract_reference,
            user=kwargs['user'],
            create=False
        )
        lead_id = kwargs.get('lead_id')
        mobile_uuid = kwargs.get('lead_mobile_uuid', None)
        this_lead = None
        if lead_id:
            this_lead = LeadGetterService.get_from_user_and_id(kwargs['user'], lead_id, strict=True)
        elif mobile_uuid:
            this_lead = LeadGetterService.get_from_user_and_properties(kwargs['user'], mobile_uuid=mobile_uuid, strict=True)
        addon_reference = kwargs.get('addon_reference', None)
        if addon_reference:
            this_addon = AddonListService.get_from_user_and_properties(kwargs['user'], reference=addon_reference, strict=True)
            if kwargs.get('amount', None):
                raise Error('For collecting cash towards add-ons you cannot provide an amount. The exact add-on value must be collected.')
            return {
                'this_device': this_addon.contract.linked_device if this_addon.contract else None,
                'amount': None,
                'client': this_addon.contract.client if this_addon.contract else None,
                'lead': this_addon.lead,
                'addon': this_addon
            }

        if not this_device and not this_lead and not this_contract:
            raise Error('You must provide either a lead_id or a device/contract')

        if not this_lead and this_device and this_device.contract is None:
            raise Error('DEVICE_NOT_REGISTERED')
        try:
            amount = Decimal(str(kwargs['amount']))
        except (KeyError, ValueError) as e:
            raise Error('INVALID_NUMBER_FORMAT') from e
        
        contract_for_payment = this_device.contract if this_device and this_device.contract else this_contract
        if contract_for_payment and contract_for_payment.status == ContractStatus.paused:
            raise Error('CONTRACT_PAUSED')
        return {'this_device': this_device, 'amount': amount,
                'contract': this_contract,
                'client': contract_for_payment.client if contract_for_payment else None, 
                'lead': this_lead,
                'addon': None
        }

    @classmethod
    def _process(cls, user, offline, time, **kwargs):
        if kwargs['lead']:
            return EditLeadService.pay_deposit_in_cash(kwargs['lead'], user, kwargs['amount'], offline, note=kwargs.get('note', ''))
        if kwargs['addon']:
            return AddonService.pay_with_cash(kwargs['addon'], user, note=kwargs.get('note', ''))
        if kwargs['contract'] and not kwargs['this_device']:
            try:
                answer, payment_made = collect_cash(
                    acting_user=user,
                    paying_client=kwargs['contract'].client,
                    amount=kwargs['amount'],
                    time=time,
                    note=kwargs.get('note', '')
                )
            except Error as error:
                return [dict({'success': False, 'status': str(error)}, **error.data)]
            answer += PaymentProcessorService.process_payment_for_target(
                payment_made,
                kwargs['contract'],
                reprocessing=False,
                error_handler=None
            )
            return answer
        return handle_paycash_request(
            acting_user=user,
            amount=kwargs['amount'],
            this_device=kwargs['this_device'],
            offline=offline,
            time=time,
            note=kwargs.get('note', '')
        )
