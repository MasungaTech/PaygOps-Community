import config
import requests
from shared.api_helpers.client_helpers.api_helper_object import APIHelper


class Doc360Service:

    CODE_GENERATION_URL = 'https://identity.document360.io/jwt/generateCode'

    @classmethod
    def get_login_link(cls, user):
        user_data = {
            "username": user.person.full_name, # as per doc its the full name
            "firstName": user.person.name,
            "lastName": user.person.surname,
            "emailId": user.username, # does not actually needs to be an email, as per doc
            "role": user.AuthorizationLevel.name, # Optional Extra variable to be used in UI if needed
            "tokenValidity": 15 
        }
        if config.ENV_VAR == 'TEST':
            code = ''
        else:
            response = requests.post(cls.CODE_GENERATION_URL, json=user_data, auth=(config.DOC360_SSO_CLIENT_ID, config.DOC360_SSO_CLIENT_SECRET))
            code = response.json().get('code')
        return config.DOC360_CALLBACK_URL+code
        