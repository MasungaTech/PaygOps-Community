from datetime import datetime, timedelta

from flask import request
from flask_login import current_user, login_required
from pony.orm import db_session, select

from constants import PAYMENT_TABS, PAYMENT_VIEWS
from core_system.client.services.client_getter_service import \
    ClientGetterService
from core_system.operational_entities.services.client_group_getter_service import \
    ClientGroupGetterService
from core_system.operational_entities.services.operational_entities_getter import \
    OperationalEntitiesGetterService
from core_system.portfolios.services.portfolio_getter_service import \
    PortfolioGetterService
from core_system.users.services.user_getter_service import UserGetterService
from payg_loan_system.payments.models.wallet import (PaymentWallet,
                                                     PaymentWalletType)
from payg_loan_system.payments.services.payment_getter_service import \
    PaymentGetterService
from payg_loan_system.payments.services.payment_sorter_service import \
    PaymentSorter
from payg_loan_system.payments.services.wallet_getter_service import \
    WalletGetterService
from payg_loan_system.payments.web_app import payment
from shared.helpers.authorizer import authorizer
from shared.helpers.clock import Clock
from shared.helpers.form_helpers import dateTimePickerToStandard
from shared.helpers.pagination import Pagination
from shared.helpers.select2 import render


@payment.route('/', methods=['GET', 'POST'])
@login_required
@authorizer('ViewPayments')
@db_session
def list_payment():

    active_tab = request.args.get('tab', 'incoming')
    paginations = {}

    entity = OperationalEntitiesGetterService.extract_from_user_and_id(current_user, request.args, "entity_id", strict=False)
    client = ClientGetterService.extract_from_user_and_id(current_user, request.args, "client_id", strict=False)
    user_collecting = UserGetterService.extract_from_user_and_id(current_user, request.args, "user_collecting_id", strict=False)
    portfolio = PortfolioGetterService.extract_from_user_and_id(current_user, request.args, "portfolio_id", strict=False)
    client_group = ClientGroupGetterService.extract_from_user_and_id(current_user, request.args, "client_group_id", strict=False)
    wallet = WalletGetterService.extract_from_user_and_id(current_user, request.args, "wallet_id", strict=False)
    view = request.args.get('view', 'all')
    source = request.args.get('payment_source', '')
    search = request.args.get('search', '')
    wallet_operator = request.args.get('wallet_operator_id', '')
    memo = request.args.get('memo', '')
    phone_number = request.args.get('phone_number', '')

    if not client:
        default_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    else:
        default_from = (datetime.now() - timedelta(days=365*10)).strftime("%Y-%m-%d")
    default_to = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    from_date_str = request.args.get('from_date', default_from)
    to_date_str = request.args.get('to_date', default_to)

    from_date = dateTimePickerToStandard(from_date_str)
    from_date_utc = Clock.localize_to_utc(from_date)
    to_date = dateTimePickerToStandard(to_date_str, '23:59')
    to_date_utc = Clock.localize_to_utc(to_date)

    for tab in PAYMENT_TABS:
        paginations[tab] = Pagination.generate(request, tab=tab, default_sort='received_on:desc')

        payments = PaymentGetterService.get_from_filtered_view(
            current_user,
            view,
            entity=entity,
            portfolio=portfolio,
            search=search,
            client_group=client_group,
            client=client,
            source=source,
            wallet=wallet,
            from_date=from_date_utc,
            to_date=to_date_utc,
            wallet_operator=wallet_operator,
            user_collecting=user_collecting,
            memo=memo,
            phone_number=phone_number,
            tab=tab
        )

        wallets = WalletGetterService.get_list(current_user)
        clients = ClientGetterService.get_list(current_user)
        operators = select(p.operator for p in PaymentWallet)
        users = UserGetterService.get_list(current_user)


        paginations[tab].objects = PaymentSorter.sort(payments, paginations[tab].sort)

    select2 = {
        'wallet_id': {
            'items': wallets,
            'text': 'FullName',
            'selected': wallet
        },
        'client_id': {
            'items': clients,
            'text': 'full_name',
            'selected': client,
            'person_search_field': True
        },
        'user_collecting_id': {
            'items': users,
            'text': 'full_name',
            'selected': user_collecting,
            'person_search_field': True
        },
        'wallet_operator_id' : {
            'items': {o or 'Empty': o or 'Empty' for o in operators},
            'raw_format': True,
        }
    }

    sources = {
        '': 'Mobile Money and Cash',
        'mobile_money': 'Mobile Money only',
        'cash': 'Cash only'
    }
    return render('list_payment.html', select2=select2,
                  paginations=paginations,
                  view=view,
                  views=PAYMENT_VIEWS,
                  wallet=wallet,
                  tabs=PAYMENT_TABS,
                  active_tab=active_tab,
                  source=source,
                  entity=entity,
                  portfolio=portfolio,
                  client_group=client_group,
                  from_date=from_date,
                  to_date=to_date,
                  search=search,
                  client=client,
                  user_collecting=user_collecting,
                  user_collectin_id=users,
                  PaymentWalletType=PaymentWalletType,
                  wallet_operator=wallet_operator,
                  memo=memo,
                  phone_number=phone_number,
                  from_date_default=default_from,
                  to_date_default=default_to,
                  sources=sources)
