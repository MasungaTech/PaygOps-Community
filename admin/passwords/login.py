from datetime import datetime
from flask_login import login_required, logout_user, current_user
from flask import request, flash, redirect, url_for, render_template, make_response
from pony.orm import db_session
import config

from core_system.users.models.user_model import User
from . import auth
from web_app import login_manager
from admin.passwords.services.user_login_services import UserLoginService
from shared.services.settings_service import SettingsService
from shared.services.two_factor_service import TwoFactorService


@login_manager.user_loader
@db_session
def load_user(user_id):
    return User.select(lambda u: u.id == user_id).prefetch(User.managed_operational_entities).get()


def get_oauth_login_url(request):
    if not config.LOGIN_PLATFORM_URL:
        return None
    oauth_login_url = config.LOGIN_PLATFORM_URL+f'?platform={config.LOGIN_PAYG_URL}&app=web'
    next = request.args.get('next')
    if next:
        oauth_login_url += f'&next={next}'
    return oauth_login_url

@auth.route("/", methods=["GET"])
@db_session
def login():
    oauth_login_url = get_oauth_login_url(request)
    return render_template('login.html', oauth_login_url=oauth_login_url)


@auth.route("/google", methods=["GET"])
@db_session
def google_login():
    oauth_login_url = get_oauth_login_url(request)
    if not oauth_login_url:
        flash('Google login is not configured')
        return redirect(url_for('login.login'))
    return redirect(oauth_login_url)


@auth.route("/refresh_jwt", methods=["GET"])
@login_required
@db_session
def refresh_jwt():
    return {'jwt': current_user.get_api_key()}


@auth.route("/auto", methods=["GET"])
@db_session
def login_auto():
    return user_login_manager(request, auto=True)


@auth.route("/", methods=["POST"])
@db_session
def login_attempt():
    return user_login_manager(request)


def user_login_manager(request, auto=False):
    success_url = request.args.get('next', url_for('index'))

    user_login = UserLoginService(request, auto=auto)
    user = user_login.user
    custom_app_query = request.args.get('custom_app', 'false').lower() == 'true'

    if user is not None or user:
        if auto and not SettingsService.get_setting('FeatureToggles').get('SSO') and not user.is_super_admin():
            flash('SSO Login is disabled on this platform')
            redirect(url_for('login.login'))
        if user.banned_time:
            minutes = user.banned_time.seconds//60
            time_msg = str(minutes)+' minutes.' if minutes else 'a few seconds.' 
            flash('Login Unsuccessful. Your account has been temporary blocked. Try again in '+
                  time_msg+' Remember that you can always&nbsp;<a href=\''+
                  url_for('login.reset_password')+'\'>reset your password</a>.')
        elif user_login.validate() == '2FA_REQUIRED':
            # Redirect to 2FA verification page
            flash('Please complete two-factor authentication to continue.')
            return redirect(url_for('login.two_fa_check', success_url=success_url, custom_app_query=custom_app_query))
        elif user_login.validate():
            return login_success(success_url, custom_app_query)
        elif user.is_expired():
            flash('Your account has expired. ')
        else:
            user.bad_login_count += 1
            user.last_bad_login_time = datetime.now()
            flash('Login Unsuccessful. Forgotten password?&nbsp;<a href=\''+
                  url_for('login.reset_password')+'\'>Get a new one</a>')
    else:
        flash('Login Unsuccessful. Make sure the username you used matches the one on your account.')
    return redirect(url_for('login.login'))


def login_success(success_url, custom_app_query=False, two_fa_required=False):
    if two_fa_required:
        user = UserLoginService(request).complete_login(two_fa_required=True)
        if not user:
            flash('Your two-factor authentication session has expired. Please log in again.')
            return redirect(url_for('login.login'))
    flash('Login Successful')
    resp = make_response(redirect(success_url))
    # Set the cookie on the response for the custom app
    if custom_app_query:
        resp.set_cookie(
            'custom_app', 
            'true', 
            expires='Fri, 01-Jan-2100 00:00:00 GMT', 
            httponly=True,       # Prevent JavaScript from accessing it
            secure=True,         # Send only over HTTPS
            samesite='None'
        )
    return resp


@auth.route('/logout')
@login_required
@db_session
def logout():
    logout_user()
    flash('Logged out')
    return redirect(url_for('login.login'))


@auth.route('/select_organisation')
@db_session
def org_selector():
    next = request.args.get('next', '')
    # This should be embedded in the app
    # but can be accessed at /login/select_organisation for getting a static HTML to embed
    return render_template('select_organisation.html', next=next)


@auth.route('/check_login')
@db_session
def check_login():
    if current_user and current_user.is_authenticated:
        response = make_response('True', 200)
    else:
        response = make_response('False', 403)
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    return response

@auth.route('2fa_check', methods=["GET", "POST"])
@db_session
def two_fa_check():
    from flask import session
    user_id = TwoFactorService.resolve_pending_login_token(session.get('2fa_token'))
    success_url = request.args.get('success_url')
    custom_app_query = True if request.args.get('custom_app_query') == 'true' else False
    if not user_id:
        session.pop('2fa_token', None)
        session.pop('2fa_user_id', None)
        flash('Your two-factor authentication session has expired. Please log in again.')
        return redirect(url_for('login.login'))
    user = User.get(id=user_id)
    if not user:
        session.pop('2fa_token', None)
        session.pop('2fa_user_id', None)
        flash('User not found')
        return redirect(url_for('login.login'))
    if not user.two_factor_enabled:
        flash('2FA is not enabled for this user')
        return redirect(url_for('login.login'))
    if request.method == 'POST':
        code = request.form.get('verification_code')
        backup_code = request.form.get('backup_code')
        if backup_code:
            # Try backup code
            if TwoFactorService.verify_backup_code(user, backup_code):
                return login_success(success_url, custom_app_query, two_fa_required=True)
            else:
                flash('Invalid backup code.', 'error')
        elif code:
            # Try TOTP code
            success, message = TwoFactorService.verify_login_code(user, code)
            if success:
                return login_success(success_url, custom_app_query, two_fa_required=True)
            else:
                flash(message, 'error')
        else:
            flash('Please enter either a verification code or backup code.', 'error')
    return render_template('2fa_check.html')