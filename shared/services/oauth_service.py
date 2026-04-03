import jwt
from config import LOGIN_JWT_SECRET


class OAuthService:

    @classmethod
    def decode_token_if_valid(cls, token):
        try:
            return jwt.decode(token, LOGIN_JWT_SECRET, algorithms=['HS256'])
        except Exception as e:
            return {}