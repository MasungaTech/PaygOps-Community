import jwt
import config
from shared.api_helpers.server_helpers.jwt_generation import decode_jwt


class StaticDownloadKeyChecker:

    @classmethod
    def check_key(cls, auth_token, permissions):
        secret = config.api_secret
        token_payload = []
        # We check the JWT signature
        try:
            token_payload = decode_jwt(auth_token, secret)
        except jwt.ExpiredSignatureError:
            return {'error': 'Signature expired. Please log in again.'}, 401
        except jwt.InvalidTokenError:
            return {'error': 'Invalid token. Please log in again.'}, 401
        # We check if the proper permissions are in the payload
        for p in permissions:
            if p not in token_payload['permissions']:
                return {'error': 'No sufficient permission. Permission missing: ' + str(p)}, 403
        return None
