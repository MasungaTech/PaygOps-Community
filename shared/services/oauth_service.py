from config import LOGIN_JWT_SECRET
from shared.api_helpers.server_helpers.jwt_generation import decode_jwt


class OAuthService:

    @classmethod
    def decode_token_if_valid(cls, token):
        try:
            return decode_jwt(token, LOGIN_JWT_SECRET)
        except Exception as e:
            return {}