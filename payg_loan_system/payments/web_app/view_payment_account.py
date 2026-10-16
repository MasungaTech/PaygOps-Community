from datetime import datetime

from flask import flash, redirect, request, url_for
from flask_login import current_user, login_required
from pony.orm import db_session

from core_system.client.services.client_getter_service import \
    ClientGetterService
from core_system.users.services.user_getter_service import UserGetterService
from payg_loan_system.contracts.models.addons_model import ContractAddOn
from payg_loan_system.contracts.services.addon_list_service import \
    AddonListService
from payg_loan_system.contracts.services.contract_getter_service import \
    ContractGetterService
from payg_loan_system.payments.models.wallet import (PaymentWallet,
                                                     PaymentWalletOwner,
                                                     PaymentWalletType)
from payg_loan_system.payments.services.payment_sorter_service import (
    PaymentSorter, ReconciledPaymentSorter)
from payg_loan_system.payments.services.wallet_getter_service import \
    WalletGetterService
from payg_loan_system.payments.web_app import payment
from sales_system.leads.services.lead_getter_service import LeadGetterService
from shared.helpers.authorizer import authorizer
from shared.helpers.pagination import Pagination
from shared.helpers.select2 import render
from shared.logger.loggers import LogAPI
from shared.services.settings_service import SettingsService


@payment.route('/account/<int:account_id>', methods=['GET'])
@login_required
@authorizer('ViewPayments')
@db_session
def account(account_id):

    selected_account = WalletGetterService.get_from_user_and_id(
        current_user, account_id, strict=True, main_resource=True
    )

    LogAPI.check_and_warn(
        selected_account.Type != PaymentWalletType.agent_collection,
        'Agent collection wallet page accessed'
    )
    contracts = ContractGetterService.get_list(current_user, awaiting_payment=True)
    leads = LeadGetterService.get_leads_ready_for_payment().order_by(
        lambda lead: lead.person.full_name
    )
    addons = AddonListService.get_list(current_user).filter(
        lambda a: a.cached_unpaid
    ).order_by(ContractAddOn.reference)
    users = UserGetterService.get_list(current_user.reload())

    payments_pagination = Pagination.generate(request, tab='payments')
    payments_pagination.sort = request.args.get('sort', 'received_on:desc')
    payments_pagination.objects = PaymentSorter.sort(
        selected_account.Payments.select(lambda p: p.Amount > 0), payments_pagination.sort
    )

    outgoing_payments = selected_account.Payments.select(lambda p: p.Amount < 0)
    outgoing_payments_pagination = Pagination.generate(request, tab='outgoing')
    outgoing_payments_pagination.sort = request.args.get('sort', 'received_on:desc')
    outgoing_payments_pagination.objects = PaymentSorter.sort(
        outgoing_payments, outgoing_payments_pagination.sort
    )
    reconciliations_pagination = Pagination.generate(request, tab='reconciliations')
    reconciliations_pagination.sort = request.args.get('sort', 'received_on:desc')
    reconciliations_pagination.objects = ReconciledPaymentSorter.sort(
        selected_account.get_reconciled_payments(), reconciliations_pagination.sort
    )

    select2 = {
        'contract_reference': {
            'items': contracts,
            'id': 'reference',
            'text': 'reference_and_name'
        },
        'addon_reference': {
            'items': addons,
            'id': 'reference',
            'text': 'reference'
        },
        'user_id': {
            'items': users,
            'text': 'full_name'
        },
        'lead_id': {
            'items': leads,
            'text': 'full_name_and_id'
        },
        'payment_reference': {
            'items': selected_account.Payments.filter(
                lambda p: p.orphaned_cached
            ),
            'text': 'label',
            'id': 'Reference',
            'data': {
                'remaining': 'remaining',
                'amount': 'Amount'
            }
        }
    }

    return render(
        'view_payment_wallet.html',
        Account=selected_account,
        select2=select2,
        PaymentWalletType=PaymentWalletType,
        total_remaining=True,
        payments_pagination=payments_pagination,
        reconciliations_pagination=reconciliations_pagination,
        outgoing_payments_pagination=outgoing_payments_pagination
    )


@payment.route('/account/<int:account_id>/edit', methods=['GET', 'POST'])
@login_required
@authorizer('EditWalletPayments')
@db_session
def edit_account(account_id):

    selected_account = WalletGetterService.get_from_user_and_id(current_user, account_id, strict=True, main_resource=True)
    print(request.form)
    if request.method == 'POST':
        if request.form.get('link_destination') and selected_account.Type not in [PaymentWalletType.agent_collection, PaymentWalletType.cash]:
            valid = True
            print(request.form)
            if request.form.get('link_destination') == 'none':
                if selected_account.client or selected_account.lead or selected_account.user:
                    selected_account.client = None
                    selected_account.lead = None
                    selected_account.user = None
                else:
                    valid = False
            elif request.form.get('link_destination') == 'client':
                this_client = ClientGetterService.get_from_user_and_id(current_user, request.form.get('clients'))
                if selected_account.client != this_client:
                    selected_account.client = this_client
                    selected_account.lead = None
                    selected_account.user = None
                else:
                    valid = False
            elif request.form.get('link_destination') == 'lead':
                this_lead = LeadGetterService.get_from_user_and_id(current_user, request.form.get('leads2'))
                if selected_account.lead != this_lead:
                    selected_account.lead = this_lead
                    selected_account.client = None
                    selected_account.user = None
                else:
                    valid = False
            elif request.form.get('link_destination') == 'user':
                user = UserGetterService.get_from_user_and_id(current_user, request.form.get('users'))
                if selected_account.user != user:
                    selected_account.lead = None
                    selected_account.client = None
                    selected_account.user = user
                else:
                    valid = False
            if valid:
                PaymentWalletOwner(
                    wallet=selected_account,
                    client=selected_account.client,
                    lead=selected_account.lead,
                    user=selected_account.user,
                    approver=current_user.reload(),
                    date=datetime.now(),
                    balance=selected_account.get_balance())
                flash('Owner changed. ')
            return redirect(url_for('.account', account_id=account_id))
        
        new_name = request.form.get('name')
        operator = request.form.get('operator')
        if PaymentWallet.get(FullName=new_name, operator=operator if operator else selected_account.operator):
            flash('Payment Wallet name already exists.')
        else:
            selected_account.FullName = request.form.get('name')
            selected_account.operator = operator if operator else selected_account.operator
            flash('Payment Wallet name changed. ')
            return redirect(url_for('.account', account_id=account_id))

    clients = ClientGetterService.get_list(current_user)
    leads2 = LeadGetterService.get_list(current_user, installed=False)
    users = UserGetterService.get_list(current_user.reload())
    wallet_operators = SettingsService.get_setting('PaymentSendingGateways').keys()

    # Create a dict with lowercase keys and original values
    wallet_operators_map = {k.lower(): k for k in wallet_operators}

    selected_client = (selected_account.client.id, selected_account.client.full_name) if selected_account.client else None
    selected_lead = (selected_account.lead.id, selected_account.lead.full_name) if selected_account.lead else None
    selected_user = (selected_account.user.id, selected_account.user.full_name) if selected_account.user else None

    select2 = {
        'clients': {
            'items': clients,
            'text': 'full_name',
            'selected': selected_client,
        },
        'leads2': {
            'items': leads2,
            'text': 'full_name',
            'selected': selected_lead,
        },
        'users': {
            'items': users,
            'text': 'full_name',
            'selected': selected_user
        }
    }

    return render(
        'edit_payment_wallet.html',
        Account=selected_account,
        select2=select2,
        PaymentWalletType=PaymentWalletType,
        wallet_operators_map=wallet_operators_map
    )
