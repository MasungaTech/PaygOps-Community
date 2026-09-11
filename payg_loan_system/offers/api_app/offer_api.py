from payg_loan_system.offers.models import Offer
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual
from payg_loan_system.offers.services.create_offer_service import CreateOfferService
from payg_loan_system.offers.services.list_offer_service import ListOfferService
from payg_loan_system.offers.services.edit_offer_service import EditOfferService
from payg_loan_system.offers.services.delete_offer_service import DeleteOfferService


class AllOffersResource(BaseAPIResourceAll):

    LIST_SERVICE = ListOfferService
    ADD_SERVICE = CreateOfferService
    LIST_PERMISSION = 'ViewOffers'
    ADD_PERMISSION = 'AddOffers'
    USE_PARENT_MODEL = False

    MODEL = Offer
    TAG = 'Offers'
    ALLOWED_API_CALLER = ["post"]
    EXTRA_LIST_PARAMS = {
        'search': {
            'in': 'query',
            'name': 'search',
            'schema': {
                'type': 'string',
            },
            'example': 'Home Loan',
            'allowEmptyValue': True,
            'description': 'Allows for filtering offers by name, code, or id'
        },
    }

class IndividualOfferResource(BaseAPIResourceIndividual):

    GET_SERVICE = ListOfferService
    EDIT_SERVICE = EditOfferService
    DELETE_SERVICE = DeleteOfferService
    GET_PERMISSION = 'ViewOffers'
    EDIT_PERMISSION = 'EditOffers'
    DELETE_PERMISSION = 'EditOffers'
    OBJECT_NAME = 'Offer'

    MODEL = Offer
    USE_PARENT_MODEL = False
    TAG = 'Offers'
