from flask_httpauth import HTTPBasicAuth
import config

monitor_auth = HTTPBasicAuth()


@monitor_auth.verify_password
def verify_credentials(username, password):
    return (username, password) == (config.apm_username, config.apm_password)