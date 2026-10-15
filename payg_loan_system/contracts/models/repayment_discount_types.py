from shared.helpers.db_helpers import TypeClassBase

class ContractRepaymentDiscountTypes(TypeClassBase):

    manual_adjustment = 'Manual Adjustment'
    special_delay = 'Special Delay'
    special_discount = 'Special Discount'
    downpayment = 'Downpayment'
    manual_delay = 'Manual Delay'
    manual_discount = 'Manual Discount'
    offer_change = 'Offer Change Discount'
    prepayment = 'Prepayment Discount'
    rounding = 'Rounding Discount'
    offer_change_delay = 'Offer Change Delay'
    reversal = 'Reversed Repayment'
    downpayment_reversal = 'Reversed Downpayment'
    purchasing_addon = 'Purchasing Add-on'
    payment_to_client = 'Payout'

    _human_codes = {
        None: 'Contract Payment',
        reversal: 'Reversed Contract Payment',
    }