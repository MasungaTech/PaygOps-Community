from .json_serialization import CustomJSONEncoder


def initialize_api_system(this_app, jwt_secret, iss_identity):
    this_app.config['iss_identity'] = iss_identity
    this_app.config['jwt_secret'] = jwt_secret
    this_app.secret_key = jwt_secret
    this_app.json_encoder = CustomJSONEncoder
    this_app.config['RESTFUL_JSON'] = {'cls': this_app.json_encoder}