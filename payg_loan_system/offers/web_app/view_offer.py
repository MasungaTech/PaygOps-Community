from flask_login import login_required, current_user
from flask import render_template, redirect, url_for, flash, request
from pony.orm import db_session, select
from payg_loan_system.offers.services.list_offer_service import ListOfferService
from shared.helpers.authorizer import authorizer

from . import offer_system
from payg_loan_system.offers.services.delete_offer_service import DeleteOfferService
from payg_loan_system.offers.models import OfferType


@offer_system.route('/<int:offer_id>', methods=['GET', 'POST'])
@login_required
@authorizer('ViewOffers')
@db_session
def view_offers(offer_id):
    this_offer = ListOfferService.get_from_user_and_id(current_user, offer_id)
    if this_offer:
        return render_template('view_offers.html', this_offer=this_offer, OfferType=OfferType)
    else:
        flash('The requested offer does not exist or you do not have the permission to see it. ')
        return redirect(url_for('offers.list_offers'))
