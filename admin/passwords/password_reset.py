from pony.orm import db_session
from flask import request, flash, redirect, url_for, render_template, \
    get_flashed_messages
from . import auth

from admin.passwords.services.password_reset_services import PasswordResetService


@auth.route("/reset_password", methods=["GET"])
@db_session
def reset_password():
    return render_template('password_reset.html')


@auth.route("/reset_password", methods=["POST"])
@db_session
def reset_password_attempt():
    error_messages = {
        'INVALID_USERNAME': 'The username provided is not registered on the platform.',
        'INVALID_CAPTCHA': 'The CAPTCHA is not valid, please try again.'
    }

    try:
        PasswordResetService.process_password_reset_request(request)
    except Exception as exception:
        this_error_message = error_messages.get(str(exception), 'There was an issue: ' + str(exception))
        flash(this_error_message)
        return redirect(url_for('login.reset_password'))
    else:
        flash('Your password has been reset, you should receive an email/sms in a few minutes with your new password. ')
        return redirect(url_for('login.login'))
