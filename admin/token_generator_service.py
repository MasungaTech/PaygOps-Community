from datetime import datetime, timedelta
import config
from shared.api_helpers.server_helpers.jwt_generation import generate_jwt


class TokenCreator:
    TOKEN_EXPIRY_SECONDS = 300

    @classmethod
    def create(cls, user, token_expiry=TOKEN_EXPIRY_SECONDS):
        datetime_in_seconds = timedelta(seconds=token_expiry)
        token_expiry_datetime = datetime.now() + datetime_in_seconds

        permissions = user.get_accessible_permissions()
        this_token = generate_jwt(user.id,
                                  permissions,
                                  'Solaris Offgrid',
                                  config.api_secret,
                                  token_expiry_datetime)
        return str(this_token)
