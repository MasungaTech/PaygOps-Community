from pony.orm.core import select, count, exists
from payg_loan_system.contracts.models.contract_status import ContractStatus
from shared.services.base_getter_service import BaseGetterService
from payg_loan_system.contracts.models.addons_model import AddOnLoanExtensionMode, AddOnOfferVersion, AddOnType


class AddonOfferVersionGetterService(BaseGetterService):

    OBJ_NAME = 'Add-on Offer Version'

    @classmethod
    def get_filtered_objects(cls, current_user, for_contract=None, for_lead=None, categories=None, **kwargs):
        if not current_user.can_access('ViewAddonOffers'):
            return AddOnOfferVersion.select(lambda a: 1==0)

        offer_versions = AddOnOfferVersion.select()

        if not for_contract and not for_lead:
            return offer_versions

        # If its for a lead or contract we filter only available for sales (taking into account entities too)
        offer_versions = offer_versions.filter(lambda ov: ov.available_for_sales)
        village = (for_lead or for_contract).person.village
        if not current_user.can_access('AddContractTermsChangeAddOns', entity=village):
            offer_versions = offer_versions.filter(lambda ov: ov.offer.type not in [AddOnType.deposit_change, AddOnType.loan_duration_change])
        contract_offer = (for_lead or for_contract).offer
        offer_versions = cls.restrict_versions_to_entities(offer_versions, "entities_allowed_for_leads", village)
        
        if for_contract:
            offer_versions = offer_versions.filter(lambda ov: ov.offer.type != AddOnType.deposit_change)
            empty_loan_contract = for_contract and for_contract.status == ContractStatus.completed and for_contract.offer.base_price_amount_can_be_negative
            if for_contract.status == ContractStatus.completed:
                if empty_loan_contract:
                    offer_versions = offer_versions.filter(lambda ov: ov.offer.type == AddOnType.lump_sum or ov.offer.loan_mode != AddOnLoanExtensionMode.duration)
                else:
                    offer_versions = offer_versions.filter(lambda ov: ov.offer.type == AddOnType.lump_sum or ov.offer.loan_mode != AddOnLoanExtensionMode.amount)
            if for_contract.add_ons.filter(lambda a: a.offer_version.offer.type == AddOnType.loan_duration_change and a.pending):
                offer_versions = offer_versions.filter(lambda ov: ov.offer.type != AddOnType.loan_duration_change)
        
        if for_lead and for_lead.addons.filter(lambda a: a.offer_version.offer.type == AddOnType.loan_duration_change):
            offer_versions = offer_versions.filter(lambda ov: ov.offer.type != AddOnType.loan_duration_change)

        if contract_offer and not contract_offer.allow_loan_addons:
            offer_versions = offer_versions.filter(lambda ov: ov.offer.type == AddOnType.lump_sum)
        if contract_offer and contract_offer.addon_offer_categories_allowed:
            descendants_categories = select(cat.descendants for cat in contract_offer.addon_offer_categories_allowed)
            offer_versions = offer_versions.filter(lambda ov: ov.offer.category in contract_offer.addon_offer_categories_allowed or ov.offer.category in descendants_categories)

        if categories:
            descendants_categories = select(cat.descendants for cat in categories)
            offer_versions = offer_versions.filter(lambda ov: ov.offer.category in categories or ov.offer.category in descendants_categories)

        return offer_versions

    @classmethod
    def restrict_versions_to_entities(cls, versions, available_entities_field, target_entity):
        not_restricted_offers_ids = select(o.id for o in versions if not getattr(o.offer, available_entities_field))[:]
        ascendant_ids = [e.id for e in target_entity.ascendants]
        restricted_offers_ids = select(o.id for o in versions if exists(getattr(o.offer, available_entities_field).filter(lambda e: e.id in ascendant_ids)))[:]
        return select(o for o in AddOnOfferVersion if o.id in not_restricted_offers_ids+restricted_offers_ids)