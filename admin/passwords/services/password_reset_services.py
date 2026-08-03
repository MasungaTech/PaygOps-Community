import os
from config import ENV_VAR
import requests
from shared.services.password_generator import PasswordGenerator
from shared.services.email_sender import EmailSender
from shared.helpers.auth_helper import encode_plaintext_password
from shared.logger.loggers import Error
from core_system.users.services.user_getter_service import UserGetterService
from messages_system.services.send_sms import SMSSend



class PasswordResetService:

    GOOGLE_CAPTCHA_SECRET_KEY = os.getenv('GOOGLE_CAPTCHA_SECRET_KEY', '')
    GOOGLE_CAPTCHA_URL = "https://www.google.com/recaptcha/api/siteverify"

    PASSWORD_RESET_SUBJECT = "Password reset request"
    PASSWORD_EMAIL_TEMPLATE = "Hello! \n\nWe have received a request to reset your password. \n" \
                              "Your new password is {new_password} \n" \
                              "You can now login into PaygOps with it. \n" \
                              "If you did not request the password change, please get in touch with support. \n\n" \
                              "Kind regards, \n" \
                              "The PaygOps Support Team\n"
    PASSWORD_SMS_TEMPLATE = "We have received a request to reset your password. \n" \
                            "Your new password is {new_password} \n" \
                            "You can now login into PaygOps with it. \n" \
                            "If you did not request the password change, please get in touch with support. \n\n" \


    @classmethod
    def process_password_reset_request(cls, request):
        username = request.form.get('username', None)
        radio_group = request.form.get('radio_group', None)
        captcha = request.form.get('g-recaptcha-response', None)
        user_ip = request.remote_addr

        this_user = UserGetterService.get_by_username(username)
        if not this_user:
            raise Error('INVALID_USERNAME')

        if not cls._is_valid_captcha(captcha, user_ip) and ENV_VAR != 'DEV':
            raise Error('INVALID_CAPTCHA')
        cls._reset_password_and_send_email_or_sms(this_user, radio_group)

    @classmethod
    def _is_valid_captcha(cls, captcha, user_ip):
        data = {
            'secret': cls.GOOGLE_CAPTCHA_SECRET_KEY,
            'response': captcha,
            'remoteip': user_ip
        }
        response = requests.post(cls.GOOGLE_CAPTCHA_URL, data=data, timeout=30)
        response_dict = response.json()
        return response_dict['success']


    @classmethod
    def _reset_password_and_send_email_or_sms(cls, this_user, radio_group):
        this_new_password = PasswordGenerator.generate_password()
        this_user.password = encode_plaintext_password(this_new_password)
        body = cls.PASSWORD_EMAIL_TEMPLATE.format(new_password=this_new_password)
        if radio_group=='email':
            if not this_user.email:
                raise Error('The user does not have an email')
            EmailSender(
                this_user.full_name,
                this_user.email,
                cls.PASSWORD_RESET_SUBJECT,
                body
            ).send()
        elif radio_group=='sms':
            number = this_user.person.preferred_phone_number()
            if not number:
                raise Error('The user does not have a phone number')
            SMSSend.SendMessage(number, cls.PASSWORD_SMS_TEMPLATE.format(new_password=this_new_password))
