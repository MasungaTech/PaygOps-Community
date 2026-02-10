from shared.services.base_getter_service import BaseGetterService
from pony.orm.core import select
from payg_loan_system.contracts.models.addon_bundle_model import ContractAddOnBundle, ContractAddOnBundleItem


class AddonBundleListService(BaseGetterService):

    OBJ_NAME = 'Add-on Bundle'

    @classmethod
    def get_filtered_objects(cls, current_user, deleted=False, category=None, for_offer=None, for_entity_lead=None, for_entity_contract=None, **kwargs):
        if not current_user.can_access('ViewAddonOffers'):
            return ContractAddOnBundle.select(lambda b: b.id == -1)
        bundles = ContractAddOnBundle.select()
        if deleted is not None: #this allows for retrieve all bundles (deleted or not) setting deleted=None 
            bundles = bundles.filter(lambda b: b.deleted == deleted)
        if for_offer and for_offer.addon_offer_categories_allowed:
            descendants_categories = select(cat.descendants for cat in for_offer.addon_offer_categories_allowed)
            bundles = bundles.filter(lambda ab: ab.category in for_offer.addon_offer_categories_allowed or ab.category in descendants_categories)
        if category:
            bundles = bundles.filter(lambda b: b in category.covered_bundles)
        if for_entity_lead:
            available_ids = select(b.id for b in bundles if b.cached_available_for_leads == 2)[:]
            available_some_entities = bundles.filter(lambda b: b.cached_available_for_leads == 1)
            if available_some_entities.count():
                entity_parents = [e.id for e in for_entity_lead.ascendants]
                for e in entity_parents:
                    ids = select(b.id for b in available_some_entities if e in b.cached_available_for_leads_entities)[:]
                    available_ids = available_ids + ids
            bundles = select(b for b in ContractAddOnBundle if b.id in available_ids)
        if for_entity_contract:
            available_ids = select(b.id for b in bundles if b.cached_available_for_contracts == 2)[:]
            available_some_entities = bundles.filter(lambda b: b.cached_available_for_contracts == 1)
            if available_some_entities.count():
                entity_parents = [e.id for e in for_entity_contract.ascendants]
                for e in entity_parents:
                    ids = select(b.id for b in available_some_entities if e in b.cached_available_for_contracts_entities)[:]
                    available_ids = available_ids + ids
            bundles = select(b for b in ContractAddOnBundle if b.id in available_ids)
        return bundles

class AddonBundleItemListService(BaseGetterService):

    OBJ_NAME = 'Add-on Bundle Item'

    @classmethod
    def get_filtered_objects(cls, current_user, **kwargs):
        return ContractAddOnBundleItem.select() if current_user.can_access('ViewAddonOffers') else ContractAddOnBundleItem.select(lambda o: o.id == -1)
