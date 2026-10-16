from flask import render_template
from flask_login import current_user, login_required
from pony.orm import db_session
from core_system.client.services.client_getter_service import ClientGetterService
from shared.helpers.authorizer import authorizer
from . import transaction_request
from payg_loan_system.contracts.services.contract_getter_service import ContractGetterService
from werkzeug.exceptions import NotFound


@transaction_request.route('/expected_paid_change/content/contract/<int:contract_id>', methods=['GET'])
@transaction_request.route('/expected_paid_change/content/<int:client_id>', methods=['GET'])
@login_required
@authorizer('ChangeExpectedPaidActions')
@db_session
def expected_paid_change_transaction_content(client_id=None, contract_id=None):
    if client_id:
        this_client = ClientGetterService.get_from_user_and_id(current_user, client_id, strict=True, main_resource=True)
        contracts = this_client.contracts.select()
    elif contract_id:
        contracts = ContractGetterService.get_filtered_objects(current_user, id=contract_id)
        if not contracts.first(): 
            raise NotFound
        this_client = contracts.first().client
    else: raise NotFound
    return render_template(
        'expected_paid_change_transaction_content.html',
        this_client=this_client,
        contracts=contracts
    )
    

