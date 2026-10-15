from flask import render_template
from flask_login import current_user, login_required
from pony.orm import db_session
from core_system.client.services.client_getter_service import ClientGetterService
from payg_loan_system.payments.services.b2c_payment_service import B2CPaymentService
from sales_system.leads.services.lead_getter_service import LeadGetterService
from shared.helpers.authorizer import authorizer
from payg_loan_system.contracts.services.contract_getter_service import ContractGetterService
from shared.helpers.select2 import render
from shared.services.settings_service import SettingsService
from . import transaction_request
from werkzeug.exceptions import NotFound


@transaction_request.route('/pay_client/content/contract/<int:contract_id>', methods=['GET'])
@transaction_request.route('/pay_client/content/<int:client_id>', methods=['GET'])
@login_required
@authorizer('PayClientActions')
@db_session
def pay_client_transaction_content(client_id=None, contract_id=None):
    if client_id:
        this_client = ClientGetterService.get_from_user_and_id(current_user, client_id, strict=True, main_resource=True)
        contracts = this_client.contracts.select()
    else:
        contracts = ContractGetterService.get_filtered_objects(current_user, id=contract_id)
    
    contract = contracts.first()
    if not contract: 
        raise NotFound
    this_client = contract.client
    wallets = B2CPaymentService.get_available_wallets(this_client.id)
    payment_gateways = SettingsService.get_setting('PaymentSendingGateways')
    leads = LeadGetterService.get_leads_ready_for_payment().filter(lambda lead: lead.person == this_client.person).order_by(
        lambda lead: lead.person.full_name
    )
    destination_contracts = ContractGetterService.get_filtered_objects(current_user, awaiting_payment=True, clients=[this_client])
    destination_contracts = destination_contracts.filter(lambda c: c.id != contract.id)
    # Only include enabled gateways
    wallet_operators_map = {k.lower(): k for k, v in payment_gateways.items() if v.get('enabled')}

    select2 = {
        'wallets': {
            'items': wallets,
            'text': 'account_phone_number',
            'data': {
                'operator': 'operator',
                'status': 'status',
            },
        },
        'leads': {
            'items': leads,
            'text': 'full_name_and_id',
        },
        'contract_reference': {
            'items': destination_contracts,
            'id': 'reference',
            'text': 'reference_and_name'
        },
    }

    amount=None
    outstanding_balance = contract.get_outstanding_balance()
    if outstanding_balance and outstanding_balance < 0:
        amount = -outstanding_balance
    return render(
        'pay_client_transaction_content.html',
        this_client=this_client,
        contracts=contracts,
        amount=amount,
        select2=select2,
        wallet_operators=wallet_operators_map,
    )
    

