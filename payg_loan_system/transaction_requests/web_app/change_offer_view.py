from flask import render_template
from flask_login import login_required, current_user
from pony.orm import db_session
from core_system.client.services.client_getter_service import ClientGetterService
from payg_loan_system.offers.services.list_offer_service import ListOfferService
from payg_loan_system.contracts.services.contract_getter_service import ContractGetterService
from shared.helpers.authorizer import authorizer
from . import transaction_request
from werkzeug.exceptions import NotFound


@transaction_request.route('/change_offer/content/contract/<int:contract_id>', methods=['GET'])
@transaction_request.route('/change_offer/content/<int:client_id>', methods=['GET'])
@login_required
@authorizer('DoChangeOfferActions')
@db_session
def change_offer_transaction_content(client_id=None, contract_id=None):
    if client_id:
        this_client = ClientGetterService.get_from_user_and_id(current_user, client_id, strict=True, main_resource=True)
        contracts = this_client.contracts.select()
    else:
        contracts = ContractGetterService.get_filtered_objects(current_user, id=contract_id)
        if not contracts.first(): 
            raise NotFound
        this_client = contracts.first().client
    offer = contracts.first().offer if contracts.count() == 1 else None
    offers = ListOfferService.get_list(current_user, in_use=True, current_offer=offer, for_client_entity=this_client.person.village)
    return render_template(
        'change_offer_transaction_content.html',
        this_client=this_client,
        offers=[[o.code, o.name] for o in offers],
        contracts=contracts
    )
