from datetime import datetime, timedelta
import jwt
import config

_DECODE_OPTIONS = {'verify_sub': False}


def generate_jwt(user_id, permissions, iss_identity, secret,
                 expiration_time=datetime.now()+timedelta(days=1, seconds=5)):
    try:
        payload = {
            'iss': iss_identity,
            'exp': expiration_time,
            'iat': datetime.now(),
            'sub': str(user_id),
            'permissions': permissions
        }
        return jwt.encode(
            payload,
            secret,
            algorithm='HS256'
        )
    except Exception as e:
        raise e


def decode_jwt(token, secret, algorithms=None):
    if algorithms is None:
        algorithms = ['HS256']
    payload = jwt.decode(
        token,
        secret,
        algorithms=algorithms,
        options=_DECODE_OPTIONS,
    )
    sub = payload.get('sub')
    if sub is not None and not isinstance(sub, int):
        payload['sub'] = int(sub)
    return payload


def generate_jwt_for_user(user, validity_seconds=None):
    if not validity_seconds:
        validity_seconds = 3600
    permissions = user.get_accessible_permissions()
    permissions.append('TestPermission')
    token_expiry_datetime = datetime.now() + timedelta(seconds=validity_seconds)
    this_token = generate_jwt(user.id, permissions, 'Solaris Offgrid',
                              config.api_secret, token_expiry_datetime)
    return this_token


if __name__ == '__main__':
    print(generate_jwt(3, ['WrongPermission'], 'Solaris Offgrid', config.api_secret,
          expiration_time=datetime.now()+timedelta(days=365*5)))
