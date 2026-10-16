from shared.logger.loggers import Error
from payg_loan_system.payments.services.reconciliation_service import ReconciliationService
from messages_system.services.message_service import MessageService
from payg_loan_system.contracts.models.contract_status import ContractStatus
from pony.orm import db_session, coalesce
from worker_app.worker_app import worker_app
from payg_loan_system.contracts.models.contract_model import Contract
from payg_loan_system.contracts.services.contract_repayment_service import ContractRepaymentService


@worker_app.task
@db_session
def try_reconcile_pending_payments(offer_id=None, contract_id=None):
    contracts = Contract.select(lambda c: c.pending_amount > 0 and c.pending_amount >= coalesce(c.offer.minimum_payment, c.reference_price))
    if offer_id:
        contracts = contracts.filter(lambda c: c.offer.id == offer_id)
    if contract_id:
        contracts = contracts.filter(lambda c: c.id == contract_id)
    print(f'Reconciling {contracts.count()} contracts with pending payments above the minimum')
    for contract in contracts:
        if contract.status == ContractStatus.completed:
            ContractRepaymentService.clear_pending_payment_if_needed(contract)
            continue
        try:
            answer = ReconciliationService.get_answer_for_contract(contract)
        except Error:
            continue
        MessageService.send_answer_to_person(answer, contract.client.person)
