from pony.orm.core import select
from payg_loan_system.contracts.models.addon_loan_extension_mode import AddOnLoanExtensionMode
from payg_loan_system.contracts.models.contract_status import ContractStatus
from payg_loan_system.contracts.services.addons.addon_offer_version_getter_service import AddonOfferVersionGetterService
from shared.services.base_getter_service import BaseGetterService
from payg_loan_system.contracts.models.addons_model import AddOnOffer, AddOnType


class AddonOfferGetterService(BaseGetterService):

    OBJ_NAME = 'Add-on Offer'

    @classmethod
    def get_filtered_objects(cls, current_user, for_contract=None, for_lead=None, **kwargs):
        # Check if the user has the 'ViewAddonOffers' permission
        if not current_user.can_access('ViewAddonOffers'):
            return AddOnOffer.select(lambda a: 1 == 0)  # No addons available if the permission is not granted

        # Get the addon offers based on the contract or lead context
        if for_contract or for_lead:
            versions = AddonOfferVersionGetterService.get_list(current_user, for_contract=for_contract, for_lead=for_lead)
            # Filter out the purchasing addons if the user doesn't have the 'AddPurchasingAddons' permission
            if not current_user.can_access('AddPurchasingAddOns'):
                versions = select(v for v in versions).filter(lambda a: not a.offer.purchasing_addon)
            # Return a query object using lambda to select the offers
            return select(v.offer for v in versions)

        # Return all addon offers, with the 'AddPurchasingAddons' filter applied
        all_offers = AddOnOffer.select()
        if not current_user.can_access('AddPurchasingAddOns'):
            all_offers = all_offers.filter(lambda a: not a.purchasing_addon)  # Filter out purchasing addons using lambda
        return all_offers

    
    @classmethod
    def formatted_addon_offer_list(cls, offers, for_bundle=False, for_contract=None, raw=False):
        from shared.services.translation_service import TranslationService
        contract_completed = for_contract and for_contract.status == ContractStatus.completed
        empty_loan_contract = for_contract and for_contract.status == ContractStatus.completed and for_contract.offer.base_price_amount_can_be_negative
        def v(o): 
            if raw: 
                return raw
            return o.version_for_bundle if for_bundle else o.version_for_sales
        return {o.id if for_bundle else o.version_for_sales.id if not raw else raw.id: {
            'name': o.name,
            'price': float(v(o).price),
            'duration_change': float(v(o).duration_change),
            'approval': o.need_approval,
            'lump': o.type == AddOnType.lump_sum,
            'duration': o.loan_mode == AddOnLoanExtensionMode.duration or (not o.loan_mode and contract_completed and not empty_loan_contract),
            'amount': o.loan_mode == AddOnLoanExtensionMode.amount or (not o.loan_mode and empty_loan_contract),
            'needs_loan_mode': o.type in [AddOnType.loan, AddOnType.deposit_change] and (not o.loan_mode and not (contract_completed or empty_loan_contract)),
            'type': TranslationService.ftext(AddOnType.to_human(o.type), current=True),
            'downpayment':float(v(o).downpayment or 0 if o.type in [AddOnType.loan, AddOnType.deposit_change] else v(o).price),
            'allow_decimal_quantities': o.allow_decimal_quantities,
            'linked_to_product': o.linked_to_product,
            'can_be_delivered': o.can_be_delivered() if o.can_be_delivered() else '',
            'purchasing_addon': o.purchasing_addon,
            'is_serialized': o.is_serialized
        } for o in offers}
