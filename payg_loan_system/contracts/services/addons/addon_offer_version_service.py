from decimal import Decimal, DecimalException
from payg_loan_system.contracts.services.addons.addon_offer_getter_service import AddonOfferGetterService
from shared.services.base_getter_service import BaseGetterService
from payg_loan_system.contracts.models.addons_model import AddOnOfferVersion, AddOnType
from shared.logger.loggers import Error
from shared.api_helpers.hook_helpers.process_hook import add_hook_after_commit
from core_system.core_entities import db
from pony.orm import flush


class AddonOfferVersionService(BaseGetterService):

    @classmethod
    def create(cls, user, offer, price, available=False, pre_sales=True, enforce_extension_limit=True, downpayment=None, duration_change=0):

        cls._validate(price, downpayment, duration_change=duration_change, offer=offer)
        if offer.type not in [AddOnType.loan, AddOnType.deposit_change] or not downpayment:
            downpayment = None
        price = Decimal(price).normalize()
        if offer.purchasing_addon and price > 0:
            price = -price
        offer_version = AddOnOfferVersion(
            offer=offer,
            price=price,
            duration_change=Decimal(duration_change).normalize(),
            available_for_registration=available in ['Yes', 'True', 'true', True],
            downpayment=downpayment,
            available_for_sales=pre_sales in ['Yes', 'True', 'true', True],
            enforce_extension_limit = enforce_extension_limit in ['Yes', 'True', 'true', True],
            version_number=offer.last_version_number+1 if offer.versions else 1
        )
        if offer_version.available_for_sales:
            flush()
            for v in offer.versions.select().filter(lambda ov: ov.available_for_sales and ov != offer_version):
                v.available_for_sales = False
        add_hook_after_commit(db, 'new_addon_offer_version', offer_version.get_serialized_object())
        return offer_version

    @classmethod
    def _add_from_data_and_user(cls, data, user):

        offer = AddonOfferGetterService.extract_from_user_and_id(user, data, 'offer_id', strict=True, empty_allowed=False)

        price = str(data.get('price', ''))
        duration_change = str(data.get('duration_change', '0'))
        available = data.get('available_for_registration', data.get('available'))
        pre_sales = data.get('available_for_sales', data.get('pre_sales'))
        enforce_extension_limit = data.get('enforce_extension_limit')
        downpayment = data.get('downpayment')

        new_offer = cls.create(user, offer, price, available, pre_sales, enforce_extension_limit, downpayment, duration_change)
        return new_offer

    @classmethod
    def edit(cls, acting_user, offer_version, price=None, available=None, pre_sales=None,
    downpayment=None, enforce_extension_limit=None, duration_change=None):

        cls._validate(price, downpayment, duration_change, offer_version=offer_version)
        if price is not None and price != offer_version.price:
            if offer_version.contract_add_ons:
                raise Error('ADDON_OFFER_HAS_ADDONS')
            offer_version.price = price
        if duration_change is not None and duration_change != offer_version.duration_change:
            if offer_version.contract_add_ons:
                raise Error('ADDON_OFFER_HAS_ADDONS')
            offer_version.duration_change = duration_change
        update_bundles = False
        if available is not None:
            offer_version.available_for_registration = available in ['Yes', 'True', 'true', True]
            update_bundles = True
        if pre_sales is not None:
            offer_version.available_for_sales = pre_sales in ['Yes', 'True', 'true', True]
            if offer_version.available_for_sales:
                for v in offer_version.offer.versions.filter(lambda ov: ov.available_for_sales and ov != offer_version):
                    v.available_for_sales = False
            update_bundles = True
        if update_bundles:
            offer_version.offer.update_bundles()
        if enforce_extension_limit is not None:
            offer_version.enforce_extension_limit = enforce_extension_limit in ['Yes', 'True', 'true', True]
        if downpayment in [0, ''] and offer_version.downpayment not in [Decimal(0), 0, None]:
            if offer_version.contract_add_ons:
                raise Error('ADDON_OFFER_HAS_ADDONS')
            offer_version.downpayment = None
        elif offer_version.offer.type in [AddOnType.loan, AddOnType.deposit_change] and downpayment is not None and downpayment != offer_version.downpayment:
            if offer_version.contract_add_ons:
                raise Error('ADDON_OFFER_HAS_ADDONS')
            offer_version.downpayment = downpayment
        if (offer_version.offer.type not in [AddOnType.loan, AddOnType.deposit_change]):
            offer_version.downpayment = None
        

    @classmethod
    def _edit_from_data_and_user(cls, offer_version, data, user):
        available = data.pop('available_for_registration', data.pop('available', None))
        pre_sales = data.pop('available_for_sales', data.pop('pre_sales', None))
        if offer_version.offer.is_system() and data:
            raise Error('CANNOT_EDIT_DEFAULT_OFFERS')
        price = data.pop('price', None)
        duration_change = data.pop('duration_change', None)
        enforce_extension_limit = data.pop('enforce_extension_limit', None)
        downpayment = data.pop('downpayment', None)
        return cls.edit(user, offer_version, price, available, pre_sales, downpayment, enforce_extension_limit, duration_change)

    @classmethod
    def make_unavailable(cls, offer_version):
        if not offer_version.available_for_registration:
            raise Error('ADDON_OFFER_ALREADY_UNAVAILABLE')
        offer_version.available_for_registration = False

    @classmethod
    def make_available(cls, offer_version):
        if offer_version.available_for_registration:
            raise Error('ADDON_OFFER_ALREADY_AVAILABLE')
        offer_version.available_for_registration = True

    @classmethod
    def _delete_from_object_and_user(cls, offer_version, user):
        if offer_version.contract_add_ons: raise Error('ADDON_OFFER_HAS_ADDONS')
        offer_version.delete()

    @classmethod
    def _validate(cls, price=None, downpayment=None, duration_change=None, offer_version=None, offer=None):

        if not offer and offer_version:
            offer = offer_version.offer

        if price is not None:
            try:
                price = Decimal(price)
            except (ValueError, TypeError, DecimalException):
                raise Error('ADDON_OFFER_PRICE_NOT_VALID', price=price)

            if price.normalize().as_tuple()[2] < -2:
                raise Error('INVALID_AMOUNT_TOO_MANY_DIGITS', amount=price, variable="price")
        
        if duration_change is not None:
            try:
                duration_change = Decimal(duration_change)
            except (ValueError, TypeError, DecimalException):
                raise Error('ADDON_DURATION_CHANGE_NOT_VALID', duration_change=duration_change)

        rprice = price if price else offer_version.price if offer_version else 0
        if offer.type == AddOnType.lump_sum and not offer.purchasing_addon and rprice < 0:
            raise Error('LUMP_SUM_NEGATIVE_PRICE', price=price)

        if offer.type in AddOnType._NO_VALUE_TYPES and rprice:
            raise Error('NO_VALUE_ADDON_WITH_PRICE', type=type, price=price)

        if downpayment:
            try:
                downpayment = Decimal(downpayment)
            except (ValueError, TypeError, DecimalException):
                raise Error('INVALID_DOWNPAYMENT', downpayment=downpayment)
            if offer.type != AddOnType.deposit_change and downpayment > Decimal(rprice):
                raise Error('INVALID_DOWNPAYMENT_TOO_HIGH', downpayment=downpayment, maximum=rprice)
            if offer.type != AddOnType.deposit_change and downpayment < 0:
                raise Error('INVALID_NEGATIVE_DOWNPAYMENT', downpayment=downpayment)
