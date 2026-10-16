from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from pony.orm import db_session, commit

from constants import PAYMENT_VIEWS
from core_system.operational_entities.services.operational_entities_getter import \
    OperationalEntitiesGetterService
from core_system.users.services.user_getter_service import UserGetterService
from payg_loan_system.reversed_payments.models import ReversedPayment
from payg_loan_system.reversed_payments.services.reversed_payments_getter_service import \
    ReversedPaymentGetterService
from payg_loan_system.reversed_payments.services.service import \
    PaymentReversalService
from payg_loan_system.reversed_payments.services.sorter import \
    ReversedPaymentSorter
from payg_loan_system.reversed_payments.web_app import reversed_payment
from shared.helpers.authorizer import authorizer
from shared.helpers.clock import Clock
from shared.helpers.form_helpers import dateTimePickerToStandard
from shared.helpers.pagination import Pagination
from shared.helpers.select2 import render


def get_datetime_from_request(name, till_end=False):
    date_str = request.args.get(name, '')
    from_date = dateTimePickerToStandard(date_str, '23:59' if till_end else '00:00')
    return from_date


@reversed_payment.route('/')
@login_required
@authorizer('ViewReversedPayments')
@db_session
def list_all():

    pagination = Pagination.generate(request, default_sort='received_on:desc')

    entity = OperationalEntitiesGetterService.extract_from_user_and_id(
        current_user, request.args, "entity_id", strict=False
    )
    status = request.args.get('status', 'unhandled')
    view = request.args.get('view', 'all')

    approver = UserGetterService.extract_from_user_and_id(
        current_user, request.args, "approver_id", strict=False)

    approvers = UserGetterService.get_list(current_user)

    select2 = {
        'approvers': {
            'items': approvers,
            'text': 'full_name',
            'person_search_field': True,
            'selected': approver
        },
    }

    if 'source' in request.args:
        return render(
            None,
            select2=select2
        )

    from_reversal_date = get_datetime_from_request('from_reversal_date')
    to_reversal_date = get_datetime_from_request('to_reversal_date', True)
    from_payment_date = get_datetime_from_request('from_payment_date')
    to_payment_date = get_datetime_from_request('to_payment_date', True)

    search_reversal_id = request.args.get('search_reversal_id', '')
    search_transaction_id = request.args.get('search_transaction_id', '')
    memo = request.args.get('memo', '')

    payment_reversals = ReversedPaymentGetterService.get_from_filtered_view(
        current_user, view, entity, status=status,
        from_reversal_date=from_reversal_date,
        to_reversal_date=to_reversal_date,
        from_payment_date=from_payment_date,
        to_payment_date=to_payment_date,
        search_reversal_id=search_reversal_id,
        search_transaction_id=search_transaction_id,
        memo=memo,
        approver=approver
    )

    pagination.objects = ReversedPaymentSorter.sort(payment_reversals, pagination.sort)

    return render(
        'list_reversed_payments.html',
        view=view,
        entity=entity,
        pagination=pagination,
        status=status,
        views=PAYMENT_VIEWS,
        from_reversal_date=from_reversal_date,
        to_reversal_date=to_reversal_date,
        from_payment_date=from_payment_date,
        to_payment_date=to_payment_date,
        approver=approver,
        search_reversal_id=search_reversal_id,
        search_transaction_id=search_transaction_id,
        memo=memo,
        select2=select2
    )


@reversed_payment.route('/<int:reversal_id>')
@login_required
@authorizer('ViewReversedPayments')
@db_session
def view_reversal(reversal_id):
    return render_template('view_reversed_payment.html',
                           rp=ReversedPayment.get_or_404(reversal_id))


@reversed_payment.route('/<int:reversal_id>/mark_handled', methods=['POST'])
@login_required
@authorizer('HandleReversedPayments', 'reversed_payment.list_all', flash_me=True)
@db_session
def mark_handled(reversal_id):
    reversal = ReversedPayment.get(id=reversal_id)
    if not reversal:
        abort(404)
    try:
        PaymentReversalService.mark_as_handled(reversal, current_user.reload())
        flash('Marked reversal with id: ' + str(reversal_id) + ' as handled')
        return redirect(url_for('reversed_payment.list_all', status='unhandled'))
    except Exception as e:
        flash(str(e), category='error')
        return redirect(url_for('reversed_payment.view_reversal', reversal_id=reversal_id))
    


@reversed_payment.route('/<int:reversal_id>/reverse', methods=['POST'])
@login_required
@authorizer('HandleReversedPayments', 'reversed_payment.list_all', flash_me=True)
@db_session
def reverse_payment(reversal_id):
    reversal = ReversedPayment.get(id=reversal_id)
    if not reversal:
        abort(404)
    try:
        PaymentReversalService.reverse_reversal(reversal, current_user.reload())
        flash('Payment reversed successfully')
        return redirect(url_for('reversed_payment.list_all', status='unhandled'))
    except Exception as e:
        flash(str(e), category='error')
        return redirect(url_for('reversed_payment.view_reversal', reversal_id=reversal_id))
