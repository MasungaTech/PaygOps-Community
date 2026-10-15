class DeviceAPIError(Exception):
    def __init__(self, value, details=None):
        self.type = value
        self.details = details

    def __str__(self):
        if self.details is not None:
            return str(self.type)+': '+str(self.details)
        return str(self.type)
