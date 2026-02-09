from decimal import Decimal, InvalidOperation
from munch import DefaultMunch
from pony import orm
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from payg_loan_system.contracts.services.addon_category_service import AddonCategoryService
from payg_loan_system.offers.services.ai_offer_creation_service import AIOfferCreationService
from payg_loan_system.offers.services.list_offer_service import ListOfferService
from shared.logger.loggers import Error
from payg_loan_system.offers.services.error_handler_service import OffersErrorHandlerService
from payg_loan_system.offers.models import LoanOffer, LumpSumOffer, Offer, OfferType, TimeBasedOffer, UsageBasedOffer
from config import DEFAULT_UNIT
from shared.helpers.form_helpers import value_to_bool
from payg_loan_system.offers.services.edit_offer_service import EditOfferService
from shared.services.base_service import BaseService
from stock_management_system.services.product_sub_type_service import ProductSubTypeService
from shared.services.settings_service import SettingsService
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService

OPT_DEC = lambda x: Decimal(x) if x else None


class CreateOfferService(BaseService):

    @classmethod
    def _add_from_data_and_user(cls, json_data, user):
        data = DefaultMunch(None, json_data)
        if data.get('ai_creation_prompt'):
            import config
            if not config.AI_ENABLED():
                raise Error("AI features are disabled. Please set the ANTHROPIC_API_KEY environment variable to enable AI features.")
            this_offer = AIOfferCreationService.create_offer(data.get('ai_creation_prompt'), data.get('offer_name'), user)
        else:
            data.code = data.code.strip()
            based_on = ListOfferService.get_from_user_and_id(user, data.based_on) if data.based_on else None
            if based_on:
                data = based_on.get_serialized_object()
                data.update(json_data)
                data = DefaultMunch(None, data)
                data.code = data.code.strip()
                if data.code == based_on.code:
                    data.code = based_on.code+'_COPY'
                if data.name == based_on.name:
                    data.name = based_on.name+' Copy'

            if not data.code:
                raise Error("OFFER_CODE_REQUIRED")
            if ' ' in data.code:
                raise Error("OFFER_CODE_HAS_SPACES")

            if orm.exists(offer for offer in Offer if offer.code == data.code):
                raise Error("OFFER_CODE_ALREADY_EXISTS")

            if data.family not in ['Home', 'Business']:
                raise Error("INVALID_OFFER_FAMILY")

            if data.panel_size_in_w:
                try:
                    data.panel_size_in_w = int(data.panel_size_in_w)
                except ValueError as error:
                    raise Error("INVALID_PANEL_SIZE") from error

            if data.battery_size_in_ah:
                try:
                    data.battery_size_in_ah = int(data.battery_size_in_ah)
                except ValueError as error:
                    raise Error("INVALID_BATERY_SIZE") from error

            this_offer = cls._create_offer(data, based_on, user=user)

        return this_offer

    @classmethod
    def _create_offer(cls, data_raw, based_on, user):
        data = EditOfferService.clean_data_for_alternate_variable_names(data_raw, data_raw.type)

        allow_pro_rata = value_to_bool(data.allow_pro_rata) if data.allow_pro_rata is not None else True
        forgive_lateness = value_to_bool(data.forgive_lateness) if data.forgive_lateness is not None else True
        base_price_amount_can_be_negative = value_to_bool(data.base_price_amount_can_be_negative) if data.base_price_amount_can_be_negative is not None else False
        
        # Validate device_type if provided
        if not DeviceAPIService.validate_device_type(data.device_type):
            available_device_types = DeviceAPIService.get_device_types_and_type_names(include_any=False)
            raise Error("INVALID_DEVICE_TYPE", data.device_type, list(available_device_types.keys()))
                
        if data.type == OfferType.loan:
            if not SettingsService.get_setting('FeatureToggles').get('NoValueLoanContracts', False):
                if base_price_amount_can_be_negative:
                    raise Error('Base price amount cannot be negative for loan contracts (feature disabled)')
            credits_given_at_start = data.get('free_credit_at_start')
            if Decimal(data.time_to_ownership_in_days) <= Decimal(credits_given_at_start):
                raise Error('Time to ownership must be higher than Free days given at start', code="INVALID_PRICING")
            if data.downpayment and Decimal(data.downpayment) < 0:
                raise Error('Initial Downpayment cannot be lower than 0')
            if data.base_price_credit == 0:
                raise Error('The reference pricing duration cannot be 0 days for a loan')
            offer = LoanOffer(
                name=data.name,
                code=data.code,
                family=data.family,
                in_use=value_to_bool(data.can_be_approved_and_registered),
                in_use_for_new_clients=value_to_bool(data.in_use_for_new_leads),
                registration_fee=cls._check_parser(data.downpayment or 0, Decimal, "INVALID_REGISTRATION_FEE"),
                time_to_ownership_in_days=cls._check_parser(data.time_to_ownership_in_days,
                                                               Decimal, "INVALID_TIME_TO_OWNERSHIP"),
                free_credit_at_start=cls._check_parser(credits_given_at_start, Decimal, "INVALID_FREE_TIME", precision=4),
                no_approval_required=not value_to_bool(data.approval_required),
                device_type=data.device_type if data.device_type and data.device_type != 'Any' else '',
                unit_cost=Decimal(data.raw_unit_cost) if data.raw_unit_cost else None,
                lighting_global_compliant=value_to_bool(data.lighting_global_compliant),
                minimum_payment=cls._check_parser(data.minimum_payment, OPT_DEC, "INVALID_MINIMUM_PRICE_AMOUNT"),
                base_price_amount=cls._check_parser(data.base_price_amount, Decimal, "INVALID_BASE_PRICE_AMOUNT"),
                base_price_credit=cls._check_parser(data.base_price_credit, Decimal, "INVALID_BASE_PRICE_TIME", precision=4),
                maximum_value_extension=cls._check_parser(data.maximum_value_extension, OPT_DEC, "INVALID_MAXIMUM_VALUE_EXTENSION"),
                discount_price_1_amount=cls._check_parser(data.discount_price_1_amount,
                                                        OPT_DEC, "INVALID_DISCOUNT_PRICE_1_AMOUNT"),
                discount_price_1_credit=cls._check_parser(data.discount_price_1_time_in_days,
                                                        OPT_DEC, "INVALID_DISCOUNT_PRICE_1_TIME", precision=4),
                discount_price_2_amount=cls._check_parser(data.discount_price_2_amount,
                                                        OPT_DEC, "INVALID_DISCOUNT_PRICE_2_AMOUNT"),
                discount_price_2_credit=cls._check_parser(data.discount_price_2_time_in_days,
                                                        OPT_DEC, "INVALID_DISCOUNT_PRICE_2_TIME", precision=4),
                panel_size_in_w=data.panel_size_in_w if data.panel_size_in_w != '' else None,
                battery_size_in_ah=data.battery_size_in_ah if data.battery_size_in_ah != '' else None,
                automatic_unlock_code_sending=value_to_bool(data.automatic_unlock_code_sending),
                notes=data.notes or '',
                parent_offer=based_on,
                allow_pro_rata=allow_pro_rata,
                forgive_lateness=forgive_lateness,
                allow_loan_addons=value_to_bool(data.allow_loan_addons if data.allow_loan_addons is not None else True),
                base_price_amount_can_be_negative=base_price_amount_can_be_negative,
                linked_to_product=value_to_bool(data.linked_to_product)
            )
        elif data.type == OfferType.time_based:
            payment_day_of_month = data.get('payment_day_of_month', None)
            if payment_day_of_month == "":
                payment_day_of_month = None
            credits_given_at_start = data.get('free_credit_at_start')
            if data.base_price_credit == 0:
                raise Error('The reference pricing duration cannot be 0 days')
            if payment_day_of_month:
                credits_given_at_start = 0
                allow_pro_rata = False
                forgive_lateness = False
            offer = TimeBasedOffer(
                name=data.name,
                code=data.code,
                family=data.family,
                in_use=value_to_bool(data.can_be_approved_and_registered),
                in_use_for_new_clients=value_to_bool(data.in_use_for_new_leads),
                registration_fee=cls._check_parser(data.downpayment, Decimal, "INVALID_REGISTRATION_FEE"),
                free_credit_at_start=cls._check_parser(credits_given_at_start, Decimal, "INVALID_FREE_TIME", precision=4),
                no_approval_required=not value_to_bool(data.approval_required),
                device_type=data.device_type if data.device_type and data.device_type != 'Any' else '',
                unit_cost=Decimal(data.raw_unit_cost) if data.raw_unit_cost else None,
                lighting_global_compliant=value_to_bool(data.lighting_global_compliant),
                minimum_payment=cls._check_parser(data.minimum_payment, OPT_DEC, "INVALID_MINIMUM_PRICE_AMOUNT"),
                base_price_amount=cls._check_parser(data.base_price_amount, Decimal, "INVALID_BASE_PRICE_AMOUNT"),
                base_price_credit=cls._check_parser(data.base_price_credit, Decimal, "INVALID_BASE_PRICE_TIME", precision=4),
                discount_price_1_amount=cls._check_parser(data.discount_price_1_amount,
                                                        OPT_DEC, "INVALID_DISCOUNT_PRICE_1_AMOUNT"),
                discount_price_1_credit=cls._check_parser(data.discount_price_1_time_in_days,
                                                        OPT_DEC, "INVALID_DISCOUNT_PRICE_1_TIME", precision=4),
                discount_price_2_amount=cls._check_parser(data.discount_price_2_amount,
                                                        OPT_DEC, "INVALID_DISCOUNT_PRICE_2_AMOUNT"),
                discount_price_2_credit=cls._check_parser(data.discount_price_2_time_in_days,
                                                        OPT_DEC, "INVALID_DISCOUNT_PRICE_2_TIME", precision=4),
                panel_size_in_w=data.panel_size_in_w if data.panel_size_in_w != '' else None,
                battery_size_in_ah=data.battery_size_in_ah if data.battery_size_in_ah != '' else None,
                automatic_unlock_code_sending=False,
                notes=data.notes or '',
                parent_offer=based_on,
                payment_frequency=data.get('payment_frequency', ''),
                allow_pro_rata=allow_pro_rata,
                payment_day_of_month=payment_day_of_month,
                forgive_lateness=forgive_lateness,
                linked_to_product=value_to_bool(data.linked_to_product)
            )
        elif data.type == OfferType.usage_based:
            if data.base_price_credit == 0:
                raise Error('The reference pricing number of credits cannot be 0')
            credits_given_at_start = data.free_credit_at_start_usage_based or data.free_credit_at_start
            if not credits_given_at_start:
                credits_given_at_start = 0
            offer = UsageBasedOffer(
                type=data.type,
                name=data.name,
                code=data.code,
                family=data.family,
                in_use=value_to_bool(data.can_be_approved_and_registered),
                in_use_for_new_clients=value_to_bool(data.in_use_for_new_leads),
                registration_fee=cls._check_parser(data.downpayment, Decimal, "INVALID_REGISTRATION_FEE"),
                free_credit_at_start=cls._check_parser(credits_given_at_start, Decimal, "INVALID_FREE_TIME", precision=4),
                no_approval_required=not value_to_bool(data.approval_required),
                device_type=data.device_type if data.device_type and data.device_type != 'Any' else '',
                unit_cost=Decimal(data.raw_unit_cost) if data.raw_unit_cost else None,
                lighting_global_compliant=value_to_bool(data.lighting_global_compliant),
                credit_unit=data.get('credit_unit', DEFAULT_UNIT),
                base_price_amount=cls._check_parser(data.base_price_amount, Decimal, "INVALID_BASE_PRICE_AMOUNT"),
                base_price_credit=cls._check_parser(data.base_price_credit, Decimal, "INVALID_BASE_PRICE_TIME", precision=4),
                discount_price_1_amount=cls._check_parser(data.discount_price_1_amount,
                                                        OPT_DEC, "INVALID_DISCOUNT_PRICE_1_AMOUNT"),
                discount_price_1_credit=cls._check_parser(data.discount_price_1_credit_in_units,
                                                        OPT_DEC, "INVALID_DISCOUNT_PRICE_1_TIME", precision=4),
                discount_price_2_amount=cls._check_parser(data.discount_price_2_amount,
                                                        OPT_DEC, "INVALID_DISCOUNT_PRICE_2_AMOUNT"),
                discount_price_2_credit=cls._check_parser(data.discount_price_2_credit_in_units,
                                                        OPT_DEC, "INVALID_DISCOUNT_PRICE_2_TIME", precision=4),
                panel_size_in_w=data.panel_size_in_w if data.panel_size_in_w != '' else None,
                battery_size_in_ah=data.battery_size_in_ah if data.battery_size_in_ah != '' else None,
                automatic_unlock_code_sending=False,
                notes=data.notes or '',
                parent_offer=based_on,
                allow_pro_rata=allow_pro_rata,
                forgive_lateness=forgive_lateness,
                linked_to_product=value_to_bool(data.linked_to_product)
            )
        elif data.type == OfferType.lump_sum:
            offer = LumpSumOffer(
                name=data.name,
                code=data.code,
                family=data.family,
                in_use=value_to_bool(data.can_be_approved_and_registered),
                in_use_for_new_clients=value_to_bool(data.in_use_for_new_leads),
                registration_fee=cls._check_parser(data.base_price_amount_lump_sum, Decimal, "INVALID_BASE_PRICE"),
                free_credit_at_start=Decimal(0),
                no_approval_required=not value_to_bool(data.approval_required),
                device_type=data.device_type if data.device_type and data.device_type != 'Any' else '',
                unit_cost=Decimal(data.raw_unit_cost) if data.raw_unit_cost else None,
                lighting_global_compliant=value_to_bool(data.lighting_global_compliant),
                base_price_amount=cls._check_parser(data.base_price_amount_lump_sum, Decimal, "INVALID_BASE_PRICE_AMOUNT"),
                base_price_credit=Decimal(1),
                discount_price_1_amount=None,
                discount_price_1_credit=None,
                discount_price_2_amount=None,
                discount_price_2_credit=None,
                panel_size_in_w=data.panel_size_in_w if data.panel_size_in_w != '' else None,
                battery_size_in_ah=data.battery_size_in_ah if data.battery_size_in_ah != '' else None,
                automatic_unlock_code_sending=False,
                notes=data.notes or '',
                parent_offer=based_on,
                allow_pro_rata=allow_pro_rata,
                forgive_lateness=forgive_lateness,
                base_price_amount_can_be_negative=base_price_amount_can_be_negative,
                linked_to_product=value_to_bool(data.linked_to_product)
            )
        else:
            raise Error("OFFER_TYPE_NOT_SUPPORTED", data.type, OfferType.to_list())

        categories_ids = data.add_allowed_addon_offer_categories_ids or []
        addon_offers_categories = AddonCategoryService.get_list(user).filter(lambda aoc: aoc.id in categories_ids)
        offer.addon_offer_categories_allowed = addon_offers_categories

        lead_entities_ids = data.add_entities_allowed_for_leads_ids or []
        lead_entities = OperationalEntitiesGetterService.get_list(user).filter(lambda aoc: aoc.id in lead_entities_ids)
        offer.entities_allowed_for_leads = lead_entities

        contract_entities_ids = data.add_entities_allowed_for_contracts_ids or []
        contract_entities = OperationalEntitiesGetterService.get_list(user).filter(lambda aoc: aoc.id in contract_entities_ids)
        offer.entities_allowed_for_contracts = contract_entities

        if data.get('product_sub_type_id'):
            product_sub_type = ProductSubTypeService.get_from_user_and_id(user, data.get('product_sub_type_id'), strict=True)
            offer.product_sub_type = product_sub_type

        return offer

    @classmethod
    def get_human_readable_message(cls, error, user=None):
        return OffersErrorHandlerService.get_human_error_message_and_log(error)

    @staticmethod
    def _check_parser(val, parser, error, precision=2):
        try:
            value = parser(val)
            if parser == Decimal:
                value = round(value, precision)
            return value
        except (TypeError, InvalidOperation):
            raise Error(str(error)+str(val))
