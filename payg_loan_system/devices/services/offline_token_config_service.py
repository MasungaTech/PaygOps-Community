from shared.logger.loggers import Error
from payg_loan_system.devices.model.offline_token_model import OfflineTokenConfig
from decimal import Decimal
from shared.services.celery_queue_service import CeleryQueueService
from shared.services.settings_service import SettingsService
from worker_app.tasks.generate_offline_tokens import refresh_offline_tokens_for_applicable_devices


class OfflineTokenConfigService:
    MAXIMUM_CONFIG_LENGTH = 5

    @classmethod
    def edit_offer_token_config(cls, config_data, offer):
        if config_data is None:
            return
        cls._check_that_config_is_valid(config_data, offer)
        cls._delete_existing_config(offer.offline_token_configs)
        for order in range(len(config_data)):
            cls._add_token_config_option(order, config_data[order], offer=offer)
        CeleryQueueService.execute_task(refresh_offline_tokens_for_applicable_devices, offer_id=offer.id)

    @classmethod
    def edit_device_type_token_config(cls, config_data, device_type):
        if config_data is None:
            return
        if device_type not in SettingsService.get_setting('AllDeviceAPIS').keys():
            raise Error('INVALID_DEVICE_TYPE')
        cls._check_that_config_is_valid(config_data)
        cls._delete_existing_config(cls.get_config_for_device_type(device_type))
        for order in range(len(config_data)):
            cls._add_token_config_option(order, config_data[order], device_type=device_type)
        CeleryQueueService.execute_task(refresh_offline_tokens_for_applicable_devices, device_type=device_type)

    @classmethod
    def get_config_for_device_type(cls, device_type):
        return OfflineTokenConfig.select().filter(lambda c: c.device_type == device_type)

    @classmethod
    def _add_token_config_option(cls, order, config_option, offer=None, device_type=None):
        value = config_option.get('value')
        OfflineTokenConfig(
            offer=offer,
            device_type=device_type,
            order=order,
            type=config_option['type'],
            credit_value=Decimal(value) if value else None,
            unit=config_option.get('unit', 'DAYS')
        )

    @classmethod
    def _delete_existing_config(cls, existing_configs):
        for existing_config in existing_configs:
            existing_config.delete()

    @classmethod
    def _check_that_config_is_valid(cls, config_data, offer=None):
        if len(config_data) > cls.MAXIMUM_CONFIG_LENGTH:
            raise Error('TOO_MANY_OFFLINE_TOKEN_CONFIG')
        if offer:
            for config_option in config_data:
                cls._check_config_option(config_option, offer)

    @classmethod
    def _check_config_option(cls, config_option, offer):
        type = config_option.get('type')
        if not type:
            return
        elif type == 'DISABLE_PAYG':
            if not offer.automatic_unlock_code_sending:
                raise Error('OFFLINE_TOKEN_DISABLE_PAYG_FORBIDDEN')
            return
        elif type == 'ADD_CREDIT':
            value = config_option.get('value')
            if not value:
                raise Error('OFFLINE_TOKEN_CONFIG_VALUE_REQUIRED')
            minimum = offer.minimum_payment if offer.minimum_payment is not None else offer.base_price_amount
            if Decimal(value) < offer.base_price_credit*minimum/offer.base_price_amount:
                raise Error('OFFLINE_TOKEN_CONFIG_VALUE_BELOW_MINIMUM')
        else:
            raise Error('INVALID_OFFLINE_TOKEN_CONFIG_TYPE')