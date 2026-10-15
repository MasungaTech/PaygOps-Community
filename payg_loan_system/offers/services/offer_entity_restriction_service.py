from shared.logger.loggers import Error


class OfferEntityRestrictionService:
    """Shared checks for offer availability by operational entity.

    Matches addon listing: unrestricted when the allowed-entities set is empty;
    otherwise the entity (or an ancestor) must be in the allowed set.
    """

    FIELD_LEADS = 'entities_allowed_for_leads'
    FIELD_CONTRACTS = 'entities_allowed_for_contracts'

    @classmethod
    def is_offer_allowed_for_entity(cls, offer, entity, field=FIELD_LEADS):
        if not offer or not entity:
            return True
        allowed_entities = getattr(offer, field, None)
        if not allowed_entities:
            return True
        try:
            if allowed_entities.count() == 0:
                return True
        except (AttributeError, TypeError):
            return True
        ascendants = getattr(entity, 'ascendants', None)
        if not ascendants:
            return True
        ascendant_ids = {e.id for e in ascendants}
        return any(allowed.id in ascendant_ids for allowed in allowed_entities)

    @classmethod
    def assert_offer_allowed_for_entity(cls, offer, entity, field=FIELD_LEADS):
        if not cls.is_offer_allowed_for_entity(offer, entity, field=field):
            raise Error(
                f'The offer {offer.name} is not available in {entity.name}.',
                code='OFFER_NOT_AVAILABLE_IN_ENTITY',
            )

    @classmethod
    def is_offer_allowed_for_lead(cls, offer, lead_village):
        return cls.is_offer_allowed_for_entity(offer, lead_village, field=cls.FIELD_LEADS)

    @classmethod
    def assert_offer_allowed_for_lead(cls, offer, lead_village):
        cls.assert_offer_allowed_for_entity(offer, lead_village, field=cls.FIELD_LEADS)

    @classmethod
    def is_offer_allowed_for_contract(cls, offer, client_village):
        return cls.is_offer_allowed_for_entity(offer, client_village, field=cls.FIELD_CONTRACTS)

    @classmethod
    def assert_offer_allowed_for_contract(cls, offer, client_village):
        cls.assert_offer_allowed_for_entity(offer, client_village, field=cls.FIELD_CONTRACTS)
