from constants import INTEGER_OPTIONAL_OPTIONS
from payg_loan_system.contracts.services.addon_list_service import AddonListService
from sales_system.leads.models.lead import Lead
from payg_loan_system.transaction_requests.services.transaction_service import BOOLEAN_SCHEMA, CONTRACT_REFERENCE_SCHEMA, DEVICE_SERIAL_SCHEMA, LEAD_ID_SCHEMA, MOBILE_UUID_SCHEMA, REQUEST_CODE_SCHEMA, TransactionService, NOTES_SCHEMA
from payg_loan_system.actions.registration import register_lead
from sales_system.leads.services.lead_getter_service import LeadGetterService
from shared.logger.loggers import Error
from shared.services.settings_service import SettingsService


class RegistrationTransactionService(TransactionService):

    type = 'registration'
    permissions = ['RegisterActions']
    description = 'Registers a contract given the `device_serial` and the `lead_id`'
    schema = {
        "properties": {
            "device_serial": DEVICE_SERIAL_SCHEMA,
            "lead_id": LEAD_ID_SCHEMA,
            "request_code": REQUEST_CODE_SCHEMA,
            "contract_mobile_uuid": MOBILE_UUID_SCHEMA,
            "note": NOTES_SCHEMA,
            "partial_addon_delivery": {
                "description": "If set to `true`, then you can select which addons are delivered or not by passing the delivered ones to `delivered_addons`.",
                "example": True,
                "type": "boolean"
            },
            "delivered_addons": {
                "description": "Is taken into account only if `partial_addon_delivery` is `true`. The list of IDs of the add-ons that were delivered at registration",
                "example": [123, 124, 125],
                "type": "array",
                    "items": {
                        "oneOf": [{"type": "integer"}, {"type": "string"},{"type": "null"}],
                    },
            },
            "send_sms_to_client": {
                **BOOLEAN_SCHEMA,
                **{'description': "Whether the result of the transaction should be sent to the client via SMS"}
            }
        },
        "required": ["lead_id"]
    }

    @classmethod
    def _validate_data(cls, **kwargs):

        lead_id = kwargs.get('lead_id', None)
        mobile_uuid = kwargs.get('lead_mobile_uuid', None)
        partial_addon_delivery = kwargs.get('partial_addon_delivery', False)
        delivered_addons = kwargs.get('delivered_addons', [])
        delivered_addons = delivered_addons if delivered_addons else []
        delivered_addons = [addon for addon in delivered_addons if addon is not None]
        delivered_addons = [AddonListService.get_from_user_and_properties(kwargs['user'], id=addon, strict=True) for addon in delivered_addons]
        undelivered_addons = []
        this_lead = None
        if lead_id:
            this_lead = LeadGetterService.get_from_user_and_id(kwargs['user'], lead_id, strict=True)
        else:
            this_lead = LeadGetterService.get_from_user_and_properties(kwargs['user'], mobile_uuid=mobile_uuid, strict=True)

        this_device = cls._get_device(kwargs.get('device_serial', ''), create=True)
        if partial_addon_delivery:
            undelivered_addons = [addon.id for addon in this_lead.not_contract_term_changes_addons if addon.id not in delivered_addons and addon.reference not in delivered_addons]        
        if not this_device:
            if (this_lead.offer and this_lead.offer.linked_to_product
                    and SettingsService.get_setting('ContractDeviceRestrictions') != 'no_device'):
                if this_lead.allocated_device:
                    this_device = this_lead.allocated_device
                else:
                    raise Error('A device could not be found with the serial number provided')

        return {'this_device': this_device, 'lead': this_lead, 'contract_mobile_uuid': kwargs.get('contract_mobile_uuid', None), 'undelivered_addons': undelivered_addons, 'delivered_addons': delivered_addons}

    @classmethod
    def _process(cls, user, offline, time, **kwargs):
        # return
        return register_lead(
            acting_user=user,
            this_device=kwargs['this_device'],
            this_lead=kwargs['lead'],
            registration_request_code=kwargs['request_code'],
            transaction=kwargs['transaction'],
            offline=offline,
            contract_mobile_uuid=kwargs['contract_mobile_uuid'],
            undelivered_addons=kwargs.get('undelivered_addons', []),
            delivered_addons=kwargs.get('delivered_addons', []),
            note=kwargs.get('note', '')
        )
