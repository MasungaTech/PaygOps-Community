from flask import render_template
from flask_login import current_user, login_required
from pony.orm import db_session
from core_system.client.services.client_getter_service import ClientGetterService
from sales_system.leads.services.lead_getter_service import LeadGetterService
from shared.helpers.authorizer import authorizer
from payg_loan_system.contracts.services.contract_getter_service import ContractGetterService
from . import transaction_request
from werkzeug.exceptions import NotFound


@transaction_request.route('/collect_cash/content/contract/<int:contract_id>', methods=['GET'])
@transaction_request.route('/collect_cash/content/<int:client_id>', methods=['GET'])
@login_required
@authorizer('CollectCashActions')
@db_session
def collect_cash_transaction_content(client_id=None, contract_id=None):
    if client_id:
        this_client = ClientGetterService.get_from_user_and_id(current_user, client_id, strict=True, main_resource=True)
        contracts = this_client.contracts.select()
    else:
        contracts = ContractGetterService.get_filtered_objects(current_user, id=contract_id)
        if not contracts.first(): 
            raise NotFound
        this_client = contracts.first().client
    return render_template(
        'collect_cash_transaction_content.html',
        this_client=this_client,
        contracts=contracts
    )
    
@transaction_request.route('/collect_cash_lead/content/<int:lead_id>', methods=['GET'])
@login_required
@authorizer('CollectCashActions')
@db_session
def collect_cash_lead_transaction_content(lead_id):
    lead = LeadGetterService.get_from_user_and_id(current_user, id=lead_id, strict=True, main_resource=True)
    return render_template('collect_cash_transaction_content.html', lead=lead)
