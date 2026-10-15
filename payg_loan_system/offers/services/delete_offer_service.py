from shared.services.base_service import BaseService


class DeleteOfferService(BaseService):

    @classmethod
    def _delete_from_object_and_user(cls, offer, user):
        if offer.used:
            offer.in_use = False
            offer.in_use_for_new_clients = False
            return
        offer.delete()
