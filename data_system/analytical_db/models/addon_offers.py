from datetime import datetime
from pony.orm import select, Set
from shared.helpers.db_helpers import Optional, PrimaryKey
from data_system.analytical_db.analytical_db import analytical_db
from payg_loan_system.contracts.models.addons_model import AddOnOffer, AddOnOfferVersion, AddOnType
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
from decimal import Decimal
import config


class AddOn_Offers(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'Add-Ons are changes to the contracts, either adding extra items with value or changing contract parameters (e.g. duration, payment amount, deposit, etc.). '

    base_model = AddOnOfferVersion

    id = PrimaryKey(int, comment="The internal unique ID of the add-on offer version")
    offer_id = Optional(int, comment="The internal unique ID of the add-on offer (identical for all versions of the offer)")
    name = Optional(str, comment="The name of the add-on offer")
    code = Optional(str, comment="The code of the add-on offer, usually a shorthand for the name for easier idenfitication")
    category = Optional(str, comment="The category of the add-on offer (defined by users)")
    type = Optional(str, comment="The type of the add-on offer (e.g. Paid Upfront, Loan Value Change, etc.)")
    loan_change_mode = Optional(str, comment="The mode of the loan change (either Reference Pricing or Duration or nothing if it can be selected when adding the add-on)")
    purchasing_addon = Optional(bool, comment="True if the add-on offer is a purchasing addon")
    available_for_leads = Optional(bool, comment="True if the add-on offer is available for new leads (in general, it might not be available in all entities)")
    available_for_contracts = Optional(bool, comment="True if the add-on offer is available for existing contracts (in general, it might not be available in all entities)")

    price_per_unit = Optional(Decimal, comment="The price per unit of the add-on offer")
    deposit_amount = Optional(Decimal, comment="The amount of the deposit for add-ons with that offer (if applicable)")

    version_number = Optional(int, comment="The number of version of the offer", default=1)
    needs_approval = Optional(bool, comment="If the add-on needs to be approved or not before taking effect")

    # Virtual (not in table)
    addons = Set('AddOns')

    # Internal
    last_updated = Optional(datetime, comment=config.LAST_UPDATED_DEFINITION)

    @staticmethod
    def converter(offer_version):
        return {
            "id": offer_version.id,
            "offer_id": offer_version.offer.id,
            "name": offer_version.offer.name,
            "code": offer_version.offer.code,
            "category": offer_version.offer.category.name if offer_version.offer.category else '',
            "type": AddOnType._get_human_readable_new(offer_version.offer.type),
            "loan_change_mode": offer_version.offer.loan_mode or '',
            "purchasing_addon": offer_version.offer.purchasing_addon,
            "available_for_leads": offer_version.available_for_sales,
            "available_for_contracts": offer_version.available_for_registration,

            "price_per_unit": offer_version.price,
            "deposit_amount": offer_version.downpayment,

            "version_number": offer_version.version_number,
            "needs_approval": offer_version.offer.need_approval,
            'last_updated': AddOn_Offers.extended_modified_date(offer_version)
        }

    @staticmethod
    def selector(objects):
        return select(offer for offer in objects).order_by(
            lambda o: AddOn_Offers.extended_modified_date(o)
        ).prefetch(AddOnOffer.category)
    
    @staticmethod
    def extended_modified_date(offer):
        return max(offer.modifiedDate, offer.offer.modifiedDate)
