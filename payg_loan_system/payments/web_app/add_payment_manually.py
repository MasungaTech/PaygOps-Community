from datetime import datetime
import os
import json
from flask_login import login_required, current_user
from pony.orm import db_session, left_join, select
from flask import request, render_template, flash, redirect, url_for, Response
from decimal import Decimal
from shared.helpers.authorizer import authorizer
from shared.helpers.select2 import render
from shared.logger.loggers import LogAPI
import config
from payg_loan_system.payments.models.wallet import PaymentWallet, PaymentWalletType
from payg_loan_system.payments.web_app import payment
from payg_loan_system.payments.services.manual_payment_add_service import ManualPaymentEntryService
from data_system.csv_exports.services.csv_export_service import CSVExportService
from pony.orm.core import MultipleObjectsFoundError
from shared.logger.loggers import Error
from werkzeug.exceptions import NotFound



Log = LogAPI()


@payment.route('/add/', methods=['GET', 'POST'])
@login_required
@authorizer('AddPayments')
@db_session
def add_manual_payment():

    if request.method == 'POST':

        payment_ref = request.form.get('payment_ref')
        payment_wallet_name = request.form.get('payment_wallet_name_list')
        payment_wallet_name_raw = request.form.get('payment_wallet_name')
        payment_msisdn = request.form.get('payment_msisdn', '')
        payment_memo = request.form.get('payment_memo', '')
        amount_raw = request.form.get('amount')
        wallet_operator = request.form.get('wallet_operator')
        reception_time = datetime.now()

        try:
            amount = Decimal(str(amount_raw))
        except Exception as error:
            flash('The amount typed is invalid. '
                  'Please double check and make sure that you use . as the decimal separator and not other symbol (no thousands separator). ', category='error')
            return redirect(url_for('payment.add_manual_payment'))

        if not payment_wallet_name:
            payment_wallet_name = payment_wallet_name_raw
        try:
            if ManualPaymentEntryService.payment_exists(payment_ref,  current_user, wallet_operator):
                flash('A payment with that reference already exists: ' + payment_ref, category='error')
            elif not payment_wallet_name:
                flash('Choose payment wallet or enter payment wallet name.', category='error')
            else:
                try:
                    ManualPaymentEntryService.add_manual_payment(
                        current_user=current_user,
                        request=request,
                        amount=amount,
                        reference=payment_ref,
                        reception_time=reception_time,
                        account_name=payment_wallet_name,
                        account_msisdn=payment_msisdn,
                        memo=payment_memo,
                        wallet_operator=wallet_operator or ''
                    )
                    flash('Payment added successfully! ')
                except Error as error:
                    flash(error.get_message())
                except Exception as exception:
                    Log.Fatal(exception)
                    flash(f'Unknown error while adding payment ({payment_ref})', category='error')
        except MultipleObjectsFoundError:
             flash(f'Multiple payments found with the same reference {payment_ref},  please provide a wallet operator', category='error')            


    accounts = left_join(account for account in PaymentWallet if account.Type == PaymentWalletType.mobile_money).order_by(lambda account: account.FullName)
    operators = select(p.operator for p in PaymentWallet)
    select2 = {
        'payment_wallet_name_list': {
            'items': accounts,
            'id': 'FullName',
            'search_field': 'composed_name',
            'text': 'composed_name_display'
        },
        'wallet_operator': {
            'items': {o or 'Empty': o or 'Empty' for o in operators},
            'raw_format': True
        }
    }

    return render('manual_payments_form.html', select2=select2)


@payment.route('/add/list')
@login_required
@authorizer('AddPayments')
@db_session
def add_manual_payment_list():

    manual_payment_logs = list(reversed(list(open(config.MANUAL_PAYMENT_LOG_PATH, 'r')))) \
        if os.path.exists(config.MANUAL_PAYMENT_LOG_PATH) else []

    return render_template('manual_payments_list.html',
                           ManualPaymentLogs=manual_payment_logs,
                           json=json)

@payment.route('/download-manual-payments-logs')
@login_required
@authorizer('AddPayments')
@db_session
def download_manual_payments_logs():    
    column_mapping = {
        'amount': 'Amount',
        'payment_ref': 'Reference',
        'mpesa_name': 'Wallet name',
        'time': 'Time',
        'memo': 'Memo',
        'user_name': 'User Name',
        'user_id': 'User ID',
        'user_ip': 'IP'
    }
    
    manual_payment_logs = list(reversed(list(open(config.MANUAL_PAYMENT_LOG_PATH, 'r')))) \
        if os.path.exists(config.MANUAL_PAYMENT_LOG_PATH) else []
    
    if not manual_payment_logs:
        raise NotFound
    
    parsed_logs = [json.loads(log) for log in manual_payment_logs if log.strip()]
    filtered_payment_logs = [{key: log[key] for key in column_mapping.keys() if key in log} for log in parsed_logs]
    renamed_payment_logs = [
        json.dumps({column_mapping[key]: value for key, value in log.items() if key in column_mapping})
        for log in filtered_payment_logs
    ]

    csv_output = CSVExportService(model=None).get_data_list_csv(renamed_payment_logs)

    response = Response(csv_output.getvalue(), mimetype='text/csv')
    filename = filename = "manual_payment_logs_%s.csv" % datetime.now().strftime("%Y_%m_%d_%H_%M")
    response.headers.set("Content-Disposition", "attachment", filename=filename)
    return response
