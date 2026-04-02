from decimal import Decimal, InvalidOperation

from munch import DefaultMunch
from pony import orm

from config import AVAILABLE_OFFER_PAYMENT_FREQUENCIES
from constants import MONTHLY_PAYMENT_FREQUENCY
from core_system.operational_entities.services.operational_entities_getter import \
    OperationalEntitiesGetterService
from payg_loan_system.contracts.services.addon_category_service import \
    AddonCategoryService
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from payg_loan_system.devices.services.offline_token_config_service import \
    OfflineTokenConfigService
from payg_loan_system.offers.models import Offer, OfferType
from payg_loan_system.offers.services.error_handler_service import \
    OffersErrorHandlerService
from sales_system.leads.models.status_category import StatusCategory
from shared.helpers.form_helpers import value_if_not_empty, value_to_bool
from shared.helpers.many_to_many_helpers import edit_many_to_many
from shared.logger.loggers import Error
from shared.services.base_service import BaseService
from shared.services.celery_queue_service import CeleryQueueService
from stock_management_system.services.product_sub_type_service import \
    ProductSubTypeService
from worker_app.tasks.try_reconcile_pending_payments import \
    try_reconcile_pending_payments
from worker_app.tasks.update_lead_statuses import update_lead_statuses
from shared.services.settings_service import SettingsService

OPT_DEC = lambda x: Decimal(x) if x not in [None, ''] else None


class EditOfferService(BaseService):
    @classmethod
    def _edit_from_data_and_user(cls, this_offer, data, user):
        if this_offer.code == 'TDO':
            raise Error('This is a default offer and cannot be edited')

        code = data.get('code', this_offer.code)
        if ' ' in code or not code:
            raise Error("OFFER_CODE_HAS_SPACES")

        if code != this_offer.code:
            if orm.exists(offer for offer in Offer if offer.code == code.strip()):
                raise Error("OFFER_CODE_ALREADY_EXISTS")

        family = data.get('family', this_offer.family)
        if family and family not in ['Home', 'Business']:
            raise Error("INVALID_OFFER_FAMILY")

        linked_to_product = data.get('linked_to_product', this_offer.linked_to_product)
        if linked_to_product != this_offer.linked_to_product:
            this_offer.linked_to_product = linked_to_product
        device_type = data.get('device_type', this_offer.device_type)
        approval_required = data.get('approval_required', not this_offer.no_approval_required)

        # Validate device_type if provided
        if not DeviceAPIService.validate_device_type(device_type):
            available_device_types = DeviceAPIService.get_device_types_and_type_names(include_any=False)
            raise Error("INVALID_DEVICE_TYPE", device_type, list(available_device_types.keys()))

        this_offer.name = data.get('name', this_offer.name)
        this_offer.code = code
        this_offer.family = family
        this_offer.in_use = value_to_bool(data.get('can_be_approved_and_registered',
                                                        this_offer.in_use))
        this_offer.in_use_for_new_clients = value_to_bool(
            data.get('in_use_for_new_leads', this_offer.in_use_for_new_clients))
        old_approval = this_offer.no_approval_required
        this_offer.no_approval_required = not value_to_bool(approval_required)
        if this_offer.type != OfferType.usage_based:
            this_offer.device_type = device_type if device_type and device_type != 'Any' else ''
        this_offer.unit_cost = value_if_not_empty(data.get('raw_unit_cost', this_offer.unit_cost))
        this_offer.lighting_global_compliant = value_to_bool(
            data.get('lighting_global_compliant', this_offer.lighting_global_compliant))
        this_offer.panel_size_in_w = value_if_not_empty(data.get('panel_size_in_w', this_offer.panel_size_in_w))
        this_offer.notes = data.get('notes', this_offer.notes) or ''
        this_offer.battery_size_in_ah = value_if_not_empty(data.get('battery_size_in_ah', this_offer.battery_size_in_ah))
        this_offer.automatic_unlock_code_sending = value_to_bool(
            data.get('automatic_unlock_code_sending', this_offer.automatic_unlock_code_sending))
        this_offer.allow_pro_rata = value_to_bool(data.get('allow_pro_rata', this_offer.allow_pro_rata))
        this_offer.forgive_lateness = value_to_bool(data.get('forgive_lateness', this_offer.forgive_lateness))

        if data.get('base_price_amount_can_be_negative'):
            base_price_amount_can_be_negative = value_to_bool(data.get('base_price_amount_can_be_negative'))
            if not SettingsService.get_setting('FeatureToggles').get('NoValueLoanContracts', False):
                if base_price_amount_can_be_negative and this_offer.type == OfferType.loan:
                    raise Error('Base price amount cannot be negative for loan contracts (feature disabled)')
            this_offer.base_price_amount_can_be_negative = base_price_amount_can_be_negative

        if this_offer.type == OfferType.loan:
            this_offer.allow_loan_addons = value_to_bool(data.get('allow_loan_addons', this_offer.allow_loan_addons))
        offline_config = data.get('offline_token_config')
        if this_offer.type == OfferType.loan:
            cls._set_properties(this_offer, data, [
                ['maximum_value_extension', 'maximum_value_extension', OPT_DEC],
            ])
        if this_offer.type in [OfferType.loan, OfferType.time_based]:
            if this_offer.allow_pro_rata:
                cls._set_properties(this_offer, data, [
                    ['minimum_payment', 'minimum_payment', OPT_DEC],
                ])
            else:
                this_offer.minimum_payment = None

        if 'product_sub_type_id' in data:
            product_sub_type = ProductSubTypeService.get_from_user_and_id(user, data['product_sub_type_id'], strict=True) if data['product_sub_type_id'] else None
            this_offer.product_sub_type = product_sub_type

        # We cleanup the data to account for alternate variable names
        data = cls.clean_data_for_alternate_variable_names(data, this_offer.type)

        if this_offer.used:
            CeleryQueueService.execute_task(try_reconcile_pending_payments, offer_id=this_offer.id)
        else:
            if this_offer.type == OfferType.usage_based:
                this_offer.device_type = device_type if device_type and device_type != 'Any' else ''
                cls._set_properties(this_offer, data, [
                    ['registration_fee', 'downpayment', Decimal],
                    ['free_credit_at_start', 'free_credit_at_start', Decimal],
                    ['base_price_amount', 'base_price_amount', Decimal],
                    ['base_price_credit', 'base_price_credit', Decimal],
                    ['discount_price_1_amount', 'discount_price_1_amount', OPT_DEC],
                    ['discount_price_1_credit', 'discount_price_1_credit', OPT_DEC],
                    ['discount_price_2_amount', 'discount_price_2_amount', OPT_DEC],
                    ['discount_price_2_credit', 'discount_price_2_credit', OPT_DEC],
                    ['credit_unit', 'credit_unit', None]
                ])

            elif this_offer.type == OfferType.lump_sum:
                cls._set_properties(this_offer, data, [
                    ['registration_fee', 'base_price_amount_lump_sum', Decimal],
                    ['base_price_amount', 'base_price_amount_lump_sum', Decimal]
                ])
            elif this_offer.type in [OfferType.loan, OfferType.time_based]:
                if this_offer.type == OfferType.time_based:
                    payment_frequency = data.get('payment_frequency')
                    payment_day_of_month = data.get('payment_day_of_month', None)
                    if payment_day_of_month == "":
                        payment_day_of_month = None
                    if payment_day_of_month:
                        data['free_credit_at_start']=0
                        this_offer.allow_pro_rata = False
                        this_offer.forgive_lateness = False
                    this_offer.payment_day_of_month = payment_day_of_month
                    if payment_frequency:
                        if payment_frequency == MONTHLY_PAYMENT_FREQUENCY:
                            offline_config = None
                        if payment_frequency in AVAILABLE_OFFER_PAYMENT_FREQUENCIES:
                            this_offer.payment_frequency = payment_frequency
                        else:
                            raise Error('Invalid payment_frequency, it should be one of the following values: '+str(AVAILABLE_OFFER_PAYMENT_FREQUENCIES.keys()))
                cls._set_properties(this_offer, data, [
                    ['registration_fee', 'downpayment', Decimal],
                    ['base_price_amount', 'base_price_amount', Decimal],
                    ['discount_price_1_amount', 'discount_price_1_amount', OPT_DEC],
                    ['discount_price_2_amount', 'discount_price_2_amount', OPT_DEC],
                    ['free_credit_at_start', 'free_credit_at_start', Decimal],
                    ['base_price_credit', 'base_price_credit', Decimal],
                    ['discount_price_1_credit', 'discount_price_1_credit', OPT_DEC],
                    ['discount_price_2_credit', 'discount_price_2_credit', OPT_DEC]
                ])
                if this_offer.registration_fee < 0:
                    raise Error('Initial Downpayment cannot be lower than 0')
                if this_offer.type == OfferType.loan:
                    cls._set_properties(this_offer, data, [
                        ['time_to_ownership_in_days', 'time_to_ownership_in_days', Decimal],
                    ])
                    if this_offer.time_to_ownership_in_days <= this_offer.free_credit_at_start:
                        raise Error('Time to ownership must be higher than Free days given at start')

        edit_many_to_many(this_offer, 'allowed_addon_offer_categories', data, AddonCategoryService.get_list(user), "addon_offer_categories_allowed")
        edit_many_to_many(this_offer, 'entities_allowed_for_leads', data, OperationalEntitiesGetterService.get_list(user, only_hierarchical=True))
        edit_many_to_many(this_offer, 'entities_allowed_for_contracts', data, OperationalEntitiesGetterService.get_list(user, only_hierarchical=True))

        OfflineTokenConfigService.edit_offer_token_config(config_data=offline_config, offer=this_offer)
        if this_offer.no_approval_required and not old_approval:
            CeleryQueueService.execute_task(update_lead_statuses, offer_id=this_offer.id, status_categories=[StatusCategory.awaiting_decision])

    @staticmethod
    def _set_properties(offer, data, properties):
        for property_name, form_field, parser in properties:
            if form_field in data:
                try:
                    value = parser(data[form_field]) if parser and data[form_field] is not None else data[form_field]
                except (TypeError, InvalidOperation):
                    raise Error('Invalid value for '+form_field)
                setattr(offer, property_name, value)

    @classmethod
    def get_human_readable_message(cls, error, user=None):
        return OffersErrorHandlerService.get_human_error_message_and_log(error)
    
    @classmethod
    def clean_data_for_alternate_variable_names(cls, data_raw, offer_type):
        if offer_type == OfferType.lump_sum:
            return data_raw
        if isinstance(data_raw, DefaultMunch):
            data_clean = data_raw.toDict()
        else:
            data_clean = data_raw
        offer_type_map = {
            OfferType.loan: 'loan',
            OfferType.usage_based: 'usage_based',
            OfferType.time_based: 'time_based'
        }
        suffix = offer_type_map.get(offer_type)
        VAR_WITH_ALT_NAMES = [
            ('free_credit_at_start', 'time_given_at_start_in_days', 'time_given_at_start_in_months'),
            ('base_price_credit', 'base_price_time_in_days', 'base_price_time_in_months', 'base_price_credit_in_units'), 
            ('discount_price_1_credit', 'discount_price_1_time_in_days', 'discount_price_1_time_in_months'), 
            ('discount_price_2_credit', 'discount_price_2_time_in_days', 'discount_price_2_time_in_months')
        ]
        for var_name in VAR_WITH_ALT_NAMES:
            if var_name[0] not in data_clean:
                if var_name[0]+'_'+suffix in data_clean:
                    data_clean[var_name[0]] = data_clean.get(var_name[0]+'_'+suffix)
                elif var_name[1] in data_clean:
                    data_clean[var_name[0]] = data_clean.get(var_name[1])
                elif var_name[2] in data_clean:
                    data_clean[var_name[0]] = data_clean.get(var_name[2])
                elif len(var_name) > 3 and var_name[3] in data_clean:
                    data_clean[var_name[0]] = data_clean.get(var_name[3])
        return DefaultMunch(None, data_clean)
