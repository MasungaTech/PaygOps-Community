from flask_login import current_user
from flask import request, redirect, url_for, render_template
from pony.orm import db_session
from shared.logger.loggers import LogAPI
from munch import Munch

from web_app import app

log = LogAPI()


@app.errorhandler(404)
@db_session
def not_found_error(error):
    error_log = Munch({})
    # We reopen a session in case it got closed by the error handler
    with db_session:
        if current_user.is_authenticated:
            return render_template('macros/404.html', error_log=error_log), 404
        else:
            return redirect(url_for('login.login'))


@app.errorhandler(500)
@db_session
def internal_error(error):
    error_log = Munch({})
    try:
        error_log = log.Fatal(error)
    except Exception as error:
        print('Unknown error while logging access: '+str(error))

    # We reopen a session in case it got closed by the error handler
    with db_session:
        if current_user.is_authenticated:
            return render_template('macros/500.html', error_log=error_log, error_code='500'), 500
        else:
            return redirect(url_for('login.login'))


@app.errorhandler(400)
@db_session
def bad_request_error(error):
    error_log = Munch({})
    try:
        error_log = log.Fatal(error)
    except Exception as error:
        print('Unknown error while logging access: ' + str(error))

    if current_user.is_authenticated:
        return render_template('macros/500.html', error_log=error_log, error_code='400'), 400
    else:
        return redirect(url_for('login.login'))
