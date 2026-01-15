import csv
import hashlib
from datetime import datetime

from flask_login import login_user
from pony.orm import db_session
from werkzeug.exceptions import Forbidden

from shared.services.oauth_service import OAuthService
from config import LOGIN_LOG_PATH, LogLogin, ENV_VAR
from core_system.users.models.user_model import User
from core_system.users.services.user_getter_service import UserGetterService
from shared.api_helpers.server_helpers.jwt_and_schema_verification import \
    check_and_load_jwt


class UserLoginService:

    def __init__(self, request, auto=False):
        self.request = request
        self.auto = auto
        if not auto:
            username = self.request.form.get('username', '')
            self.password = self.request.form.get('password', '')
            with db_session:
                self.user = UserGetterService.get_by_username(username)
        else:
            # This is for login from central login
            if request.args.get('key'):
                key_data = OAuthService.decode_token_if_valid(request.args.get('key'))
                email = key_data.get('email')
                with db_session:
                    self.user = UserGetterService.get_by_email(email)
            # This is for login as your own user with API key
            elif request.args.get('api_key'):
                key_data = check_and_load_jwt(request.args.get('api_key'))
                sub = key_data.get('sub')
                with db_session:
                    self.user = User.get(id=sub)
            # This is for login as another user with the special keys
            else:
                login_user_key = request.args.get('parent_key')
                decoded_key = check_and_load_jwt(login_user_key)
                if decoded_key['sub'] != 0:
                    with db_session:
                        user = User.get(id=decoded_key['sub'])
                        if user.username == 'system@solarisoffgrid.com':
                            raise Forbidden('You are not allowed to access this resource.')
                        if user.is_super_admin():
                            target_user = User.get(id=request.args.get('login_as'))
                            if target_user and user.can_access('EditUsers', person=target_user.person):
                                self.user = target_user

    def validate(self):
        if self.user.is_expired() or self.user.username == 'system@solarisoffgrid.com':
            return None
        if ENV_VAR != 'TEST' and self.user.is_super_admin() and not self.auto:
            return None
        if (not self.auto and self.valid_password()) or (self.auto and self.valid_key()):
            # Check if 2FA is required
            if self.user.two_factor_enabled and not self.auto:
                # Set session flags for 2FA verification
                from flask import session
                session['2fa_user_id'] = self.user.id
                # Don't login yet, redirect to 2FA verification
                return '2FA_REQUIRED'
            else:
                # Normal login flow
                return self.complete_login()
        return None
    
    def complete_login(self, two_fa_required=False):
        if two_fa_required:
            from flask import session
            user_id = session.get('2fa_user_id')
            if user_id:
                self.user = User.get(id=user_id)
                session.pop('2fa_user_id', None)
        login_user(self.user)
        self.user.bad_login_count = 0
        self.user.last_bad_login_time = None
        if LogLogin:
            self.log_login()
        return self.user

    def valid_password(self):
        if self.user:
            return self.user.password == hashlib.sha256(self.password.encode('utf-8')).hexdigest()
        return False

    def valid_key(self):
        if self.user:
            return True
        return False

    def log_login(self):
        login_log = dict(user_name=self.user.full_name.encode('utf-8'),
                         user_id=self.user.id,
                         time=str(datetime.now())
                         )

        login_log['user_agent'] = str(self.request.user_agent)
        login_log['user_ip'] = str(self.request.environ.get('HTTP_X_REAL_IP', self.request.remote_addr))
        f = open(LOGIN_LOG_PATH, 'a')
        fieldnames = ['user_name', 'user_id', 'time', 'user_agent', 'user_ip']
        logwriter = csv.DictWriter(f, delimiter=';', quotechar='|', quoting=csv.QUOTE_MINIMAL, fieldnames=fieldnames)
        logwriter.writerow(login_log)
