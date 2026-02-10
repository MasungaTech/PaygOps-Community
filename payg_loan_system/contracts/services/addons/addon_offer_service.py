from pony import orm

from constants import NON_PAYG_TYPE
from core_system.core_entities import db
from core_system.operational_entities.services.operational_entities_getter import \
    OperationalEntitiesGetterService
from payg_loan_system.contracts.models.addon_category import AddOnCategory
from payg_loan_system.contracts.models.addons_model import (
    AddOnLoanExtensionMode, AddOnOffer, AddOnType, ContractAddOn)
from payg_loan_system.contracts.services.addon_category_service import \
    AddonCategoryService
from payg_loan_system.contracts.services.addon_service import AddonService
from payg_loan_system.contracts.services.addons.addon_offer_getter_service import \
    AddonOfferGetterService
from payg_loan_system.contracts.services.addons.addon_offer_version_service import \
    AddonOfferVersionService
from shared.api_helpers.hook_helpers.process_hook import add_hook_after_commit
from shared.helpers.many_to_many_helpers import edit_many_to_many
from shared.helpers.string_helper import strtobool
from shared.logger.loggers import Error
from shared.services.base_service import BaseService
from shared.services.settings_service import SettingsService
from stock_management_system.services.product_sub_type_service import \
    ProductSubTypeService


class AddonOfferService(BaseService):

    NOT_PURCHASING_CATEGORY_ERROR = 'You can only use a category that is a child of the “Purchasing” category for purchasing add-ons'

    @classmethod
    def create(
        cls, user, name, code, price, category, type, need_approval=False, available=False, loan_mode='',
        pre_sales=True, enforce_extension_limit=True, downpayment=None, based_on=None,
        entities_for_leads_ids=None, entities_for_contracts_ids=None, duration_change=0,
        allow_decimal_quantities=True, force=False, linked_to_product=False, product_type='',
        product_sub_type_id=None, purchasing_addon=False
    ):
       
        if strtobool(linked_to_product):
            if not SettingsService.get_setting('NPGDeviceEnabled'):
                raise Error('You cannot link add-ons to products if Non Paygo Devices are not enabled')
            if not product_type:
                product_type = NON_PAYG_TYPE
            if product_type != NON_PAYG_TYPE:
                raise Error(
                    'Invalid product type {type}, only Non Paygo Devices Allowed',
                    type=product_type
                )
        product_sub_type = ProductSubTypeService.get_from_user_and_id(
            user, product_sub_type_id, strict=True
        ) if product_sub_type_id else None

        if strtobool(purchasing_addon) and not category:
            category = AddOnCategory.get(name='Purchasing')
            
        cls._validate(
            code, category, type, loan_mode, force=force, linked_to_product=linked_to_product,
            product_type=product_type, product_sub_type=product_sub_type,
            purchasing_addon=purchasing_addon
        )
        offer = AddOnOffer(
            name=name,
            code=code,
            category=category,
            type=type,
            need_approval=need_approval in ['Yes', 'True', 'true', True],
            loan_mode=loan_mode,
            allow_decimal_quantities=allow_decimal_quantities,
            based_on=based_on,
            linked_to_product=linked_to_product,
            product_type=product_type,
            product_sub_type=product_sub_type,
            purchasing_addon=purchasing_addon
        )

        if type not in [AddOnType.loan, AddOnType.deposit_change] or not downpayment:
            downpayment = None
        AddonOfferVersionService.create(
            user, offer, price, available, pre_sales, enforce_extension_limit,
            downpayment, duration_change
        )

        if entities_for_leads_ids:
            offer.entities_allowed_for_leads = OperationalEntitiesGetterService.get_list(
                user
            ).filter(lambda oe: oe.id in entities_for_leads_ids)
        if entities_for_contracts_ids:
            offer.entities_allowed_for_contracts = OperationalEntitiesGetterService.get_list(
                user
            ).filter(lambda oe: oe.id in entities_for_contracts_ids)
        offer.update_bundles() # We do it here rather than in a trigger to avoid issues with sets
        add_hook_after_commit(db, 'new_addon_offer', offer.get_serialized_object())
        return offer

    @classmethod
    def _add_from_data_and_user(cls, data, user, force=False):

        name = data.get('name')
        code = data.get('code')
        based_on = AddonOfferGetterService.extract_from_user_and_id(user, data, 'based_on_id')

        b = lambda p: getattr(based_on, p) if based_on else None
        category_name = data.get('category', 'Purchasing')
        category: AddOnOffer = AddonCategoryService.get_from_user_and_properties(user, name=category_name, strict=True) if category_name else b('category')
        if category and category.is_system() and not force:
            raise Error('CANNOT_PUT_OFFER_IN_DEFAULT_CATEGORY')
        
        type = data.get('type') or b('type') or data.get('payment_mode') or ''
        loan_mode = data.get('loan_mode') or b('loan_mode') or ''
        need_approval = data.get('need_approval') or b('need_approval')

        allow_decimal_quantities = data.get('allow_decimal_quantities') or b('allow_decimal_quantities')
        allow_decimal_quantities = allow_decimal_quantities in ['Yes', 'True', 'true', True]
        entities_for_leads_ids = data.get('add_entities_allowed_for_leads_ids', data.get('entities_allowed_for_leads_ids'))
        entities_for_contracts_ids = data.get('add_entities_allowed_for_contracts_ids', data.get('entities_allowed_for_contracts_ids'))
        purchasing_addon = data.get('purchasing_addon') or b('purchasing_addon')
        purchasing_addon = purchasing_addon in ['Yes', 'True', 'true', True]

        linked_to_product = data.get('linked_to_product') or b('linked_to_product') or False
        product_type = data.get('product_type') or b('product_type') or ''
        product_sub_type_id = data.get('product_sub_type_id') or (b('product_sub_type').id if b('product_sub_type') else None) or None
        blv = lambda p: getattr(based_on.last_version, p) if based_on else None

        price = str(data.get('price') if 'price' in data else (blv('price') or ''))
        duration_change = str(data.get('duration_change') or blv('duration_change') or '') or 0
        available = data.get('available_for_registration', data.get('available')) or blv('available_for_registration')
        pre_sales = data.get('available_for_sales', data.get('pre_sales')) or blv('available_for_sales')
        enforce_extension_limit = data.get('enforce_extension_limit') or blv('enforce_extension_limit')
        downpayment = data.get('downpayment') or blv('downpayment')

        if based_on:
            if data.get('disable_base_offer_for_leads', False):
                cls.disable_all_for_sales(user, based_on)
            if data.get('disable_base_offer_for_contracts', False):
                cls.disable_all_for_registration(user, based_on)
            if entities_for_leads_ids is None:
                entities_for_leads_ids = [o.id for o in based_on.entities_allowed_for_leads]
            if entities_for_contracts_ids is None:
                entities_for_contracts_ids = [o.id for o in based_on.entities_allowed_for_contracts]

        new_offer = cls.create(
            user, name, code, price, category, type, need_approval, available, loan_mode=loan_mode,
            pre_sales=pre_sales, enforce_extension_limit=enforce_extension_limit,
            downpayment=downpayment, entities_for_leads_ids=entities_for_leads_ids or [],
            entities_for_contracts_ids=entities_for_contracts_ids or [], based_on=based_on,
            duration_change=duration_change, allow_decimal_quantities=allow_decimal_quantities,
            force=force, linked_to_product=linked_to_product, product_type=product_type,
            product_sub_type_id=product_sub_type_id, purchasing_addon=purchasing_addon
        )

        if based_on and data.get('replace_base_offer_in_bundles', True):
            for bundle_item in based_on.bundle_items:
                bundle_item.offer = new_offer
        return new_offer

    @classmethod
    def disable_all_for_sales(cls, user, offer):
        for version in offer.versions.filter(lambda v: v.available_for_sales):
            AddonOfferVersionService.edit(user, version, pre_sales=False)

    @classmethod
    def disable_all_for_registration(cls, user, offer):
        for version in offer.versions.filter(lambda v: v.available_for_registration):
            AddonOfferVersionService.edit(user, version, available=False)

    @classmethod
    def edit(
        cls, acting_user, offer: AddOnOffer, name=None, code=None, category='', type=None, loan_mode=None,
        need_approval=None, based_on=False, allow_decimal_quantities=None, linked_to_product=None,
        product_sub_type_id=None, product_type=None, purchasing_addon=None, **kwargs
    ):

        product_sub_type = ProductSubTypeService.get_from_user_and_id(
            acting_user, product_sub_type_id, strict=True
        ) if product_sub_type_id else None
        cls._validate(
            code, category, type, loan_mode, offer, linked_to_product,
            product_type, product_sub_type, purchasing_addon
        )
        if offer and offer.is_system():
            raise Error('CANNOT_EDIT_DEFAULT_OFFERS')
        if name is not None:
            offer.name = name
        if code is not None:
            offer.code = code
        if category != '':
            offer.category = category
        if type is not None and offer.type != type:
            if offer.addons_count:
                raise Error('ADDON_OFFER_HAS_ADDONS')
            offer.type = type
        if need_approval is not None:
            old_approval_status = offer.need_approval
            offer.need_approval = need_approval in ['Yes', 'True', 'true', True]
            if old_approval_status and not offer.need_approval:
                versions = [v.id for v in offer.versions]
                addons = ContractAddOn.select(
                    lambda a: a.pending and a.contract and a.offer_version.id in versions
                )
                for addon in addons:
                    AddonService.approve(addon, acting_user)
        if loan_mode is not None and loan_mode != offer.loan_mode:
            if offer.addons_count:
                raise Error('ADDON_OFFER_HAS_ADDONS')
            offer.loan_mode = loan_mode
        if allow_decimal_quantities is not None:
            if offer.addons_count:
                raise Error('ADDON_OFFER_HAS_ADDONS')
            offer.allow_decimal_quantities = allow_decimal_quantities in ['Yes', 'True', 'true', True]
        if purchasing_addon is not None:
            offer.purchasing_addon = strtobool(purchasing_addon)
        if based_on is not False:
            offer.based_on = based_on
        if linked_to_product is not None and linked_to_product != offer.linked_to_product:
            if offer.addons_count:
                raise Error('ADDON_OFFER_HAS_ADDONS')
            offer.linked_to_product = linked_to_product in ['Yes', 'True', 'true', True]
        if offer.linked_to_product:
            if not SettingsService.get_setting('NPGDeviceEnabled'):
                raise Error('You cannot link add-ons to products if Non Paygo Devices are not enabled')
            if not product_type:
                product_type = NON_PAYG_TYPE
            if product_type != NON_PAYG_TYPE:
                raise Error(
                    'Invalid product type {type}, only Non Paygo Devices Allowed',
                    type=product_type
                )
            if product_type is not None and product_type != offer.product_type:
                raise Error('ADDON_OFFER_HAS_ADDONS')
            offer.product_type = product_type
            if product_sub_type is not None and product_sub_type != offer.product_sub_type:
                raise Error('ADDON_OFFER_HAS_ADDONS')
            offer.product_sub_type = product_sub_type
        else:
            offer.product_sub_type = None
            offer.product_type = ''

        possible_entities = OperationalEntitiesGetterService.get_list(
            acting_user, only_hierarchical=True
        )
        edit_many_to_many(offer, 'entities_allowed_for_leads', kwargs, possible_entities)
        edit_many_to_many(offer, 'entities_allowed_for_contracts', kwargs, possible_entities)
        offer.update_bundles() # We do it here rather than in a trigger to avoid issues with sets

    @classmethod
    def _edit_from_data_and_user(cls, offer, data, user):
        name = data.pop('name', None)
        code = data.pop('code', None)
        category_name = data.pop('category', '')
        category = AddonCategoryService.get_from_user_and_properties(
            user, name=category_name, strict=True
        ) if category_name else category_name
        type = data.pop('type', None) or data.pop('payment_mode', None)
        loan_mode = data.pop('loan_mode', None)
        need_approval = data.pop('need_approval', None)
        based_on = data.pop('based_on', None)
        allow_decimal_quantities = data.pop('allow_decimal_quantities', None)
        purchasing_addon = data.pop('purchasing_addon', None)
        linked_to_product = data.pop('linked_to_product', False)
        product_sub_type_id = data.pop('product_sub_type_id', None) or None
        product_type = data.pop('product_type', None) or None
        return cls.edit(
            user, offer, name, code, category, type, loan_mode, need_approval,
            based_on, allow_decimal_quantities, linked_to_product, product_sub_type_id,
            product_type, purchasing_addon, **data
        )

    @classmethod
    def _delete_from_object_and_user(cls, offer, user):
        if ContractAddOn.select(lambda a: a.offer_version.offer == offer): 
            raise Error('ADDON_OFFER_HAS_ADDONS')
        for version in offer.versions:
            version.delete()
        offer.delete()

    @classmethod
    def _validate(cls, code, category='', type=None, loan_mode=None, offer=None, linked_to_product=False,
                  product_type=None, product_sub_type=None, purchasing_addon=None, force=False):

        if code and ' ' in code:
            raise Error("ADDON_OFFER_CODE_HAS_SPACES", code=code)

        if code and (not offer or code != offer.code) and orm.exists(
            o for o in AddOnOffer if o.code == code.strip()
        ):
            raise Error("ADDON_OFFER_CODE_ALREADY_EXISTS", offer_code=code)

        if type is not None and not AddOnType.valid(type):
            raise Error('INVALID_ADDON_OFFER_TYPE', type=type, allowed=AddOnType.to_list())

        if loan_mode is not None and not AddOnLoanExtensionMode.ovalid(loan_mode):
            raise Error('INVALID_LOAN_MODE', loan_mode=loan_mode)

        if category and not isinstance(category, AddOnCategory):
            raise Error('INVALID_CATEGORY')

        if category and category.is_system():
            if not force:
                raise Error('CANNOT_PUT_OFFER_IN_DEFAULT_CATEGORY')
        if offer:
            linked_to_product = linked_to_product if linked_to_product is not None else offer.linked_to_product
            product_type = product_type if product_type is not None else offer.product_type
            product_sub_type = product_sub_type if product_sub_type is not None and offer.product_sub_type else None
            purchasing_addon = purchasing_addon if purchasing_addon is not None else offer.purchasing_addon
            category = category if category is not None else offer.category
            type = type if type is not None else offer.type


        if linked_to_product and product_sub_type:
            if product_sub_type.is_serialized:
                cls._validate_serialized_addons(product_type, product_sub_type, purchasing_addon)
            else:
                cls._validate_non_serialized_addons(product_type)
            
        if linked_to_product and product_sub_type and not product_sub_type.is_serialized:
            cls._validate_non_serialized_addons(product_type)

        if purchasing_addon and type != AddOnType.lump_sum:
            raise Error('PURCHASING_ADDON_ONLY_ALLOWED_FOR_LUMP_SUM')

        if purchasing_addon and not cls._is_purchasing_category(category):
            raise Error(cls.NOT_PURCHASING_CATEGORY_ERROR)
        if not purchasing_addon and cls._is_purchasing_category(category):
            raise Error(cls.NOT_PURCHASING_CATEGORY_ERROR)

    @classmethod
    def _validate_serialized_addons(cls, product_type=None, product_sub_type=None, purchasing_addon=False):
        if product_sub_type and product_sub_type.device_type != product_type:
            raise Error('PRODUCT_MODEL_DEVICE_TYPE_MISMATCH')
        if product_sub_type and not product_sub_type.is_serialized:
            raise Error('You can only used serialized product types with add-on offers.')
        if (product_sub_type or product_type) and purchasing_addon:
            raise Error('You cannot assign product type to purchasing add-ons.')
        
    @classmethod
    def _validate_non_serialized_addons(cls, product_type=None):
        if product_type and product_type != 'NPG' :
            raise Error('Product Type must be of type NPG')

    @classmethod
    def _is_purchasing_category(cls, category):
        # We loop through the parents to find if the category is a child of the Purchasing category
        while category:
            if category.name == 'Purchasing':
                return True
            category = category.parent
        return False