from flask import render_template
from flask_login import current_user, login_required
from pony.orm import db_session
from core_system.client.services.client_getter_service import ClientGetterService
from payg_loan_system.contracts.services.contract_getter_service import ContractGetterService
from payg_loan_system.contracts.models.contract_status import ContractStatus
from shared.helpers.authorizer import authorizer
from . import transaction_request


@transaction_request.route('/pause/content/contract/<int:contract_id>', methods=['GET'])
@transaction_request.route('/pause/content/<int:client_id>', methods=['GET'])
@login_required
@authorizer('PauseContractActions')
@db_session
def pause_transaction_content(client_id=None, contract_id=None):
    if client_id:
        this_client = ClientGetterService.get_from_user_and_id(current_user, client_id, strict=True, main_resource=True)
        contracts = this_client.contracts.filter(lambda c: c.status not in [ContractStatus.completed, ContractStatus.cancelled, ContractStatus.paused])
    else:
        contracts = ContractGetterService.get_filtered_objects(current_user, id=contract_id)
    return render_template('pause_contract_transaction_content.html', contracts=contracts)