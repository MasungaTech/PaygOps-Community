class APIError(Exception):
    def __init__(self, value):
        self.type = value
        super().__init__(value)

    def __str__(self):
        return str(self.type)

class APINetworkingError(APIError):
    pass


class APIAuthorizationError(APIError):
    pass


class APIResourcePermissionError(APIError):
    pass


class APIRemoteServerError(APIError):
    pass

class APIInvalidInputError(APIError):
    pass


class ObjectDoesNotExist(Exception):
    pass
