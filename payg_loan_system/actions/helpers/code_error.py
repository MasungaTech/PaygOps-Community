from shared.logger.loggers import LogAPI

log_api = LogAPI()


class ConfigurationError(Exception):
    def __init__(self, value):
        self.type = value

    def __str__(self):
        return str(self.type)


KNOWN_ERRORS = ["CLIENT_HAS_NO_DEVICE", "CLIENT_HAS_SEVERAL_DEVICE", "DEVICE_NOT_PREREGISTERED",
                "DEVICE_TYPE_NOT_SPECIFIED", "DEVICE_TYPE_NOT_SUPPORTED",
                "REMOTE_SERVER_ERROR", "INVALID_ACTIVATION_REQUEST_CODE",
                "INVALID_REGISTRATION_REQUEST_CODE", 'INVALID_CODE_TYPE_ACTIVATION', 
                'DEVICE_NOT_FOUND_OR_NOT_RECOGNIZED', 'DEVICE_NOT_EXIST_OR_NOT_ALLOWED']


def handle_device_code_error(SolarisCodeError):
    if str(SolarisCodeError) in KNOWN_ERRORS:
        return {
            "success": False,
            "status": str(SolarisCodeError)
        }
    log_api.FatalNoRequest(SolarisCodeError)
    return {
        'success': False,
        'status': 'UNKNOWN_ERROR',
        'error_message': str(SolarisCodeError)
    }
