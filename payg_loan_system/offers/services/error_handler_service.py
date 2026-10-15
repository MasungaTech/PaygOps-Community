from shared.logger.loggers import LogAPI


class OffersErrorHandlerService:
    error_messages = {
        'OFFER_CODE_REQUIRED': 'The code of the offer is required. ',
        'OFFER_CODE_ALREADY_EXISTS': 'The specified offer code is already in use by another offer, '
                                     'please choose an other one or modify the other offer.',
        'INVALID_TIME_TO_OWNERSHIP': 'The time to ownership entered is not a valid number. ',
        'INVALID_INVALID_REGISTRATION_FEE': 'The downpayment entered is not a valid number. ',
        'INVALID_FREE_TIME': 'The free time given at start entered is not a valid number. ',
        'INVALID_MINIMUM_PRICE_AMOUNT': 'The minimum payment amount entered is not a valid number. ',
        'INVALID_BASE_PRICE_AMOUNT': 'The base price amount entered is not a valid number. ',
        'INVALID_BASE_PRICE_TIME': 'The base price time entered is not a valid number. ',
        'INVALID_MAXIMUM_VALUE_EXTENSION': 'The maximum value extension is not a valid number',
        'INVALID_PRICING': 'The pricing you have entered is invalid; check that both amounts and time are filled '
                           'and that the pricing follows the rules specified on the form.',
        'OFFER_TYPE_NOT_SUPPORTED': 'The specified offer type is not currently supported by your platform. ',
        'OFFER_CODE_HAS_SPACES': 'The specified offer code cannot contain spaces.',
        'INVALID_OFFER_FAMILY': 'The specified offer family is not "Home" or "Business".',
        'INVALID_PANEL_SIZE': 'The panel size must be an integer number.',
        'INVALID_BATERY_SIZE': 'The batery size must be an integer number.',
        'INVALID_BASE_PRICE': 'The base price of the offer is not a valid number.',
        
        'INVALID_DEVICE_TYPE': 'The device type is not valid.',
        'TOO_MANY_OFFLINE_TOKEN_CONFIG': 'You cannot add more offline token configs.',
        'OFFLINE_TOKEN_DISABLE_PAYG_FORBIDDEN': 'Disable Payg Tokens are disable for offline mode.',
        'OFFLINE_TOKEN_CONFIG_VALUE_REQUIRED': 'You need to provide a value for the offline token.',
        'OFFLINE_TOKEN_CONFIG_VALUE_BELOW_MINIMUM': 'The value provided for the offline token is below the offer reference value.',
        'INVALID_OFFLINE_TOKEN_CONFIG_TYPE': 'The offline token config type is invalid.',
        'MINIMUM_PRICE_ABOVE_REFERENCE_PRICE': 'The mimimum price cannot be above the reference price.'
    }

    @classmethod
    def get_human_error_message_and_log(cls, exception):
        if str(exception) in cls.error_messages:
            this_error_message = cls.error_messages.get(str(exception))
        else:
            this_error_message = 'There was an issue while saving: '+str(exception)
            try:
                raise Exception('Unhandled error in Offers: '+str(exception)) from exception
            except Exception as reraised:
                LogAPI().Fatal(reraised)
        return this_error_message
