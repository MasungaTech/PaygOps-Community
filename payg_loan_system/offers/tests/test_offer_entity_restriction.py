import pytest
from pony.orm import db_session, flush

from core_system.operational_entities.services.edit_operational_entity_service import EditOperationalEntityService
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from core_system.users.services.user_getter_service import UserGetterService
from payg_loan_system.offers.services.create_offer_service import CreateOfferService
from payg_loan_system.offers.services.list_offer_service import ListOfferService
from payg_loan_system.offers.services.offer_entity_restriction_service import OfferEntityRestrictionService
from shared.logger.loggers import Error


class TestOfferEntityRestriction:

    LOAN_FIELDS = {
        'time_to_ownership_in_days': 365,
        'downpayment': 30,
        'time_given_at_start_in_days': 5,
        'base_price_amount': 5,
        'base_price_time_in_days': 1,
        'discount_price_1_amount': 6,
        'discount_price_1_time_in_days': 2,
    }
    LUMP_FIELDS = {
        'base_price_amount_lump_sum': 5,
    }
    COMMON_FIELDS = {
        'family': 'Home',
        'can_be_approved_and_registered': True,
        'in_use_for_new_leads': True,
        'in_use': True,
        'approval_required': False,
        'device_type': 'NPG',
        'raw_unit_cost': 2000,
        'lighting_global_compliant': True,
    }

    @classmethod
    def _create_offer(cls, user, offer_type, code, extra=None, lead_entity_ids=None, contract_entity_ids=None):
        type_fields = cls.LOAN_FIELDS if offer_type == 'Loan' else cls.LUMP_FIELDS
        data = {
            'name': code,
            'code': code,
            'type': offer_type,
            **cls.COMMON_FIELDS,
            **type_fields,
        }
        if lead_entity_ids is not None:
            data['entities_allowed_for_leads_ids'] = lead_entity_ids
        if contract_entity_ids is not None:
            data['entities_allowed_for_contracts_ids'] = contract_entity_ids
        if extra:
            data.update(extra)
        offer = CreateOfferService.add_from_data_and_user(data, user)
        flush()
        return offer

    @db_session
    @pytest.mark.parametrize('offer_type', ['Loan', 'Lump Sum'])
    def test_list_offer_service_filters_by_lead_entity(self, offer_type):
        user = UserGetterService.get_by_username('super_admin@test.com')
        village = OperationalEntitiesGetterService.get_list(user, level=0).first()
        other_village = EditOperationalEntityService.add_from_data_and_user({
            'name': f'Other Village List {offer_type}',
            'level': 0,
            'parent_id': village.parent.id,
        }, user)
        flush()

        restricted = self._create_offer(
            user, offer_type, f'RESTR_LIST_{offer_type.replace(" ", "_")}',
            lead_entity_ids=[other_village.id],
        )
        allowed = self._create_offer(
            user, offer_type, f'ALLOW_LIST_{offer_type.replace(" ", "_")}',
            lead_entity_ids=[village.id],
        )
        unrestricted = self._create_offer(
            user, offer_type, f'FREE_LIST_{offer_type.replace(" ", "_")}',
        )

        offers = list(ListOfferService.get_list(user, for_lead_entity=village))
        offer_ids = {o.id for o in offers}
        assert allowed.id in offer_ids
        assert unrestricted.id in offer_ids
        assert restricted.id not in offer_ids

        # Parent restriction includes child village via ascendants
        parent_restricted = self._create_offer(
            user, offer_type, f'PARENT_LIST_{offer_type.replace(" ", "_")}',
            lead_entity_ids=[village.parent.id] if village.parent else [village.id],
        )
        offers = list(ListOfferService.get_list(user, for_lead_entity=village))
        assert parent_restricted.id in {o.id for o in offers}

    @db_session
    def test_list_offer_service_keeps_current_offer_even_if_restricted(self):
        user = UserGetterService.get_by_username('super_admin@test.com')
        village = OperationalEntitiesGetterService.get_list(user, level=0).first()
        other_village = EditOperationalEntityService.add_from_data_and_user({
            'name': 'Other Village Current Offer',
            'level': 0,
            'parent_id': village.parent.id,
        }, user)
        flush()
        restricted = self._create_offer(
            user, 'Loan', 'CURRENT_RESTRICTED_OFFER',
            lead_entity_ids=[other_village.id],
        )
        offers = list(ListOfferService.get_list(
            user, for_lead_entity=village, current_offer=restricted
        ))
        assert restricted.id in {o.id for o in offers}

    @db_session
    @pytest.mark.parametrize('offer_type', ['Loan', 'Lump Sum'])
    def test_assert_offer_allowed_for_lead(self, offer_type):
        user = UserGetterService.get_by_username('super_admin@test.com')
        village = OperationalEntitiesGetterService.get_list(user, level=0).first()
        other_village = EditOperationalEntityService.add_from_data_and_user({
            'name': f'Other Village Assert {offer_type}',
            'level': 0,
            'parent_id': village.parent.id,
        }, user)
        flush()

        unrestricted = self._create_offer(user, offer_type, f'FREE_ASSERT_{offer_type.replace(" ", "_")}')
        OfferEntityRestrictionService.assert_offer_allowed_for_lead(unrestricted, village)

        allowed = self._create_offer(
            user, offer_type, f'ALLOW_ASSERT_{offer_type.replace(" ", "_")}',
            lead_entity_ids=[village.id],
        )
        OfferEntityRestrictionService.assert_offer_allowed_for_lead(allowed, village)

        restricted = self._create_offer(
            user, offer_type, f'RESTR_ASSERT_{offer_type.replace(" ", "_")}',
            lead_entity_ids=[other_village.id],
        )
        with pytest.raises(Error) as error:
            OfferEntityRestrictionService.assert_offer_allowed_for_lead(restricted, village)
        assert error.value.code == 'OFFER_NOT_AVAILABLE_IN_ENTITY'
