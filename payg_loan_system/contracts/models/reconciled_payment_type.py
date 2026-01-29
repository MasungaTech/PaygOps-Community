from shared.helpers.db_helpers import TypeClassBase


class ReconciledPaymentType(TypeClassBase):
    repayment = 'Repayment'
    repayment_reversal = 'Repayment reversal'
    repayment_pending = 'Repayment (Pending)'
    payment_reversal = 'Payment reversal'
    initial_payment = 'Downpayment'
    downpayment_reversal = 'Downpayment reversal'
    payment_client_reversal = 'Payout reversal'
    addon = 'Addon'
    user = 'User'
    user_reversal = 'User Reversal'
    manual_debit = 'Manual Debit'
    manual_adjustment = 'Manual Adjustment'
    repayment_pending_reversal = 'Pending repayment reversal'
    addon_payment_reversal = 'Add-on payment reversal'
    blocked_during_lead_editing = 'Money blocked during lead edition'
    blocked_during_lead_editing_reversal = 'Money blocked during lead edition reversal'
    payment_pending_reconciliation = 'Payment pending reconciliation'
    payment_pending_reconciliation_reversal = 'Payment pending reconciliation reversal'
    purchasing_addon = 'Purchasing add-on'
    payment_to_client = 'Payout'

    _human_codes = {
        repayment: 'Contract Payment',
        repayment_reversal: 'Contract Payment Reversal',
        repayment_pending: 'Contract Payment (Pending)',
        addon: 'Add-On',
        repayment_pending_reversal: 'Pending Contract Payment Reversal',
    }