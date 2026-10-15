from datetime import datetime
from pony.orm import select, Set
from shared.helpers.db_helpers import Optional, PrimaryKey
from data_system.analytical_db.analytical_db import analytical_db
from payg_loan_system.contracts.models.addons_model import AddOnType, ContractAddOn
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
from decimal import Decimal
import config


class AddOns(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'Add-Ons are changes to the contracts, either adding extra items with value or changing contract parameters (e.g. duration, payment amount, deposit, etc.). '

    base_model = ContractAddOn

    id = PrimaryKey(int, comment="The internal unique ID of the add-on")
    reference = Optional(str, comment="The unique reference of the add-on")

    contract_id = Optional('Contracts', comment="The ID of the contract on which the add-on is", column="contract_id")
    contract_reference = Optional(str, comment="The reference of the contract on which the add-on is")
    lead_id = Optional('Leads', csv_columns=[("Lead/Client Name", lambda c: c.full_name)], comment="The ID of the lead on which the add-on is", column="lead_id")
    sold_to = Optional(str, comment="Whether the add-on was sold at the lead stage (before the contract started) or after the contract was registered. The possible values are either \"Lead\" or \"Contract\"")

    status = Optional(str, comment="The status of the add-on (e.g. if it's pending payment, canceled, etc.)")
    delivered =  Optional(bool, comment="The delivery status of the addon")
    planned_delivery_date = Optional(datetime, force_time=True, comment="The date at which the add-on is planned to be delivered")
    delivered_date = Optional(datetime, force_time=True, comment="The date at which the add-on was delivered")
    
    creation_date = Optional(datetime, comment="The date at which the add-on was created")
    approval_date = Optional(datetime, comment="The date at which the add-on was approved")
    payment_date = Optional(datetime, comment="The date at which the add-on was paid (or partially paid)")
    canceled_date = Optional(datetime, comment="The date at which the add-on was canceled")

    entry_by_user_id = Optional('Users', csv_columns=[("Entry by", lambda l: l.full_name)], reverse='add_ons_sold', comment="The ID of the user who sold the add-on", column="entry_by_user_id")
    approved_by_user_id = Optional('Users', csv_columns=[("Approved by", lambda l: l.full_name)], reverse='add_ons_approved', comment="The ID of the user who approved the sale of the add-on", column="approved_by_user_id")

    offer_id = Optional('AddOn_Offers', csv_columns=[("Offer Name", lambda l: l.name)], comment="The ID of the add-on offer of the add-on (the kind of add-on)", column="offer_id")

    unit_price = Optional(Decimal, comment="The unit price of the add-on (for a quantity of 1)")
    quantity_sold = Optional(Decimal, comment="The quantity of the add-on sold")
    total_value = Optional(Decimal, comment="The total value of that add-on (unit price * quantity sold)")
    amount_of_discounts = Optional(Decimal, comment="The amount of discounts that were applied to the add-on")
    amount_paid_without_discounts = Optional(Decimal, comment="The amount that was actually paid for the add-on (not including any amount that was discounted)")

    loan_change_mode = Optional(str, comment="The mode of the loan change if the add-on offer can change the contract by either adjusting the Reference Pricing or Duration")
    deposit_amount = Optional(Decimal, comment="The part of the total value that was paid as a deposit (if applicable)")
    loan_duration_days_change = Optional(float, comment="The number of days the loan was extended by the add-on (if applicable)")
    reference_pricing_amount_change = Optional(Decimal, comment="The changes in the amount of the reference pricing caused by the add-on (if applicable)")

    note = Optional(str, comment="A free-form note about the add-on")
    stock_item_id = Optional("Stock_Items", comment="The Internal ID of the Stock Item linked to this add-on, if relevant")

    # Virtual (not in table)
    reconciled_payments = Set('Reconciled_Payments')

    # Internal
    last_updated = Optional(datetime, comment=config.LAST_UPDATED_DEFINITION)

    @staticmethod
    def _derive_loan_change_mode(addon):
        mode = addon.loan_mode or addon.offer_version.loan_mode
        if mode:
            return mode

        offer_type = addon.offer_version.offer.type
        if offer_type == AddOnType.loan_duration_change:
            return 'Duration'
        if offer_type in [AddOnType.loan, AddOnType.deposit_change]:
            # When no fixed mode is stored, sales can choose either mode.
            return 'Duration and Reference Pricing'
        return ''

    @staticmethod
    def converter(addon):
        return {
            "id": addon.id,
            "reference": addon.reference,

            "contract_id": addon.contract.id if addon.contract else None,
            "contract_reference": addon.contract.reference if addon.contract else '',
            "lead_id": addon.lead.id if addon.lead else addon.contract.lead.id,
            "sold_to": "Lead" if addon.lead else "Contract",

            "creation_date": addon.time_created,
            "approval_date": addon.time_approved,
            "payment_date": addon.time_paid,
            "canceled_date": addon.time_canceled,
            "delivered": addon.delivered,

            "offer_id": addon.offer_version.id,

            "unit_price": addon.offer_version.price,
            "quantity_sold": addon.quantity_sold,
            "total_value": addon.total_amount or 0,
            "amount_of_discounts": addon.discounted_amount or 0,
            "amount_paid_without_discounts": addon.already_paid or 0,

            "approved_by_user_id": addon.sale_approved_by.id if addon.sale_approved_by else None,
            "entry_by_user_id": addon.sale_made_by.id if addon.sale_made_by else None,

            'note': addon.note or '',
            'loan_change_mode': AddOns._derive_loan_change_mode(addon),
            'status': config.ADDONS_STATUSES_NAMES_ALL.get(addon.status, addon.status) or '',
            'planned_delivery_date': addon.derived_planned_delivery_date(),
            'delivered_date': addon.delivery_date if addon.delivery_date else None,

            'deposit_amount': addon.offer_version.downpayment*addon.quantity_sold if addon.offer_version.downpayment else None,
            'loan_duration_days_change': addon.extension_days,
            'reference_pricing_amount_change': addon.repayment_increase,

            'stock_item_id': addon.device.stock_item.id if addon.device else None,

            'last_updated': AddOns.extended_modified_date(addon)
        }

    @staticmethod
    def selector(objects):
        return select(addon for addon in objects).order_by(lambda a: AddOns.extended_modified_date(a)).prefetch(ContractAddOn.offer_version)
    
    @staticmethod
    def extended_modified_date(addon):
        return max(
            addon.modifiedDate,
            addon.offer_version.modifiedDate,
            addon.offer_version.offer.modifiedDate
        )
