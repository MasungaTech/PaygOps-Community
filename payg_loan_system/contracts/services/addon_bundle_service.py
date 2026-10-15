from decimal import Decimal, DecimalException
from payg_loan_system.contracts.services.addon_bundle_list_service import AddonBundleListService
from payg_loan_system.contracts.services.addons.addon_offer_getter_service import AddonOfferGetterService
from payg_loan_system.contracts.services.addon_category_service import AddonCategoryService
from pony import orm
from shared.logger.loggers import Error
from payg_loan_system.contracts.models.addon_bundle_model import ContractAddOnBundle, ContractAddOnBundleItem
from payg_loan_system.contracts.models.addons_model import AddOnType
from shared.services.base_service import BaseService


class AddonBundleService(BaseService):

    @classmethod
    def _add_from_data_and_user(cls, data, user):
        this_bundle = ContractAddOnBundle(name=data['name'])
        return this_bundle

    @classmethod
    def _edit_from_data_and_user(cls, this_bundle, data, user):
        if 'name' in data:
            this_bundle.name = data['name']
        if 'category' in data:
            category_name = data['category']
            category = None
            if category_name:
                category = AddonCategoryService.get_from_user_and_properties(user, name=category_name, strict=True)
            this_bundle.category = category
        return this_bundle

    @classmethod
    def _delete_from_object_and_user(cls, this_bundle, user):
        this_bundle.deleted = True
        return this_bundle


class AddonBundleItemService(BaseService):

    @classmethod
    def _add_from_data_and_user(cls, data, user):
        return cls._process_from_data(user, data)

    @classmethod
    def _edit_from_data_and_user(cls, this_bundle_item, data, user):
        return cls._process_from_data(user, data, this_bundle_item)
    
    @classmethod
    def _delete_from_object_and_user(cls, item, user):
        bundle = item.bundle
        item.delete()
        bundle.update_cached_data()

    @classmethod
    def _process_from_data(cls, user, data, this_bundle_item=None):
        bundle = AddonBundleListService.extract_from_user_and_id(user, data, 'bundle_id', strict=True)
        offer_id = data.get('offer_id', data.get('offer'))
        offer = AddonOfferGetterService.get_from_user_and_id(user, offer_id) if offer_id else None
        if not offer:
            offer = AddonOfferGetterService.get_from_user_and_properties(user, code=data.get('offer_code')) if data.get('offer_code') else None
        if not offer and (offer_id or data.get('offer_code')):
            raise Error('AddonOffer not found')
        quantity_sold = data.get('quantity_sold')
        loan_mode = data.get('loan_mode', '')
        return cls._edit(bundle, offer, quantity_sold, loan_mode, this_bundle_item)

    @classmethod
    def _edit(cls, bundle, offer, quantity_sold, loan_mode, item_to_edit=None):

        if quantity_sold:
            try:
                quantity_sold = Decimal(str(quantity_sold)).normalize()
            except (ValueError, TypeError, DecimalException):
                raise Error('The quantity_sold must be a valid decimal number.')
            if round(quantity_sold, 2) != quantity_sold:
                raise Error('The quantity_sold must have only two decimal digits.')
            if round(quantity_sold, 2) == 0:
                raise Error('The quantity sold must not be zero.')

        val_offer = (offer or item_to_edit.offer)

        if offer and not loan_mode:
            loan_mode = ''

        if loan_mode and val_offer.type != AddOnType.loan:
            raise Error('Loan extension option are only available for Loan addons')

        if val_offer.type == AddOnType.loan and loan_mode is None:
            raise Error('Loan extension option is required')

        if not item_to_edit:
            existing = orm.select(item for item in ContractAddOnBundleItem if item.offer == offer and item.bundle == bundle).first()
            if existing:
                raise Error(f'An item with the same offer already exists in this bundle with id {existing.id}. Please just edit it.')

        if not item_to_edit:
            item_to_edit = ContractAddOnBundleItem(
                bundle=bundle,
                offer=offer,
                quantity_sold=quantity_sold,
                loan_mode=loan_mode
            )
            item_to_edit.bundle.update_cached_data()
        else:
            if bundle:
                old_bundle = item_to_edit.bundle
                item_to_edit.bundle = bundle
                old_bundle.update_cached_data()
                item_to_edit.bundle.update_cached_data()
            if offer:
                item_to_edit.offer = offer
                item_to_edit.bundle.update_cached_data()
            if quantity_sold:
                item_to_edit.quantity_sold = quantity_sold
            if loan_mode is not None:
                item_to_edit.loan_mode = loan_mode
        return item_to_edit
        
