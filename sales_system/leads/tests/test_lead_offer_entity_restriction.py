import pytest
from pony.orm import db_session, flush

from core_system.operational_entities.services.edit_operational_entity_service import EditOperationalEntityService
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from core_system.users.services.user_getter_service import UserGetterService
from payg_loan_system.offers.services.create_offer_service import CreateOfferService
from sales_system.lead_generator.model import LeadGenerator
from sales_system.leads.services.add_lead_service import AddLeadService
from sales_system.leads.services.edit_lead_service import EditLeadService
from shared.helpers.client_creator import ClientCreator
from shared.logger.loggers import Error


class TestLeadOfferEntityRestriction:

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
        'approval_required': False,
        'device_type': 'NPG',
        'raw_unit_cost': 2000,
        'lighting_global_compliant': True,
    }

    @classmethod
    def _create_offer(cls, user, offer_type, code, lead_entity_ids=None):
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
        return CreateOfferService.add_from_data_and_user(data, user)

    @classmethod
    def _unique_phone(cls, seed):
        # Match test DB phone length: +234 + 10 digits
        return f'+234{int(seed) % 10_000_000_000:010d}'

    @classmethod
    def _lead_base_data(cls, user, village, offer_id=None, phone=None):
        if not getattr(user.person, 'leadGenerator'):
            LeadGenerator(person=user.person, type=2)
            flush()
        phone = phone or cls._unique_phone(offer_id or 1999888777)
        data = {
            'name': 'Entity',
            'surname': 'Restriction',
            'l0_entity_id': village.id,
            'generator': user.person.leadGenerator.id,
            'gender': 'Male',
            'status': 'Very Interested',
            'preferred_phone_number': phone,
        }
        if offer_id is not None:
            data['offer'] = offer_id
        return data

    @db_session
    @pytest.mark.parametrize('offer_type', ['Loan', 'Lump Sum'])
    def test_add_lead_rejects_restricted_offer(self, offer_type):
        user = UserGetterService.get_by_username('super_admin@test.com')
        village = OperationalEntitiesGetterService.get_list(user, level=0).first()
        other_village = EditOperationalEntityService.add_from_data_and_user({
            'name': f'Other Village AddLead {offer_type}',
            'level': 0,
            'parent_id': village.parent.id,
        }, user)
        flush()
        offer = self._create_offer(
            user, offer_type, f'RESTR_ADD_{offer_type.replace(" ", "_")}',
            lead_entity_ids=[other_village.id],
        )
        flush()
        with pytest.raises(Error) as error:
            AddLeadService.add_lead(
                self._lead_base_data(user, village, offer.id, phone=self._unique_phone(1888000000 + offer.id)),
                user,
            )
        assert error.value.code == 'OFFER_NOT_AVAILABLE_IN_ENTITY'

    @db_session
    @pytest.mark.parametrize('offer_type', ['Loan', 'Lump Sum'])
    def test_add_lead_allows_matching_and_unrestricted_offers(self, offer_type):
        user = UserGetterService.get_by_username('super_admin@test.com')
        village = OperationalEntitiesGetterService.get_list(user, level=0).first()

        matching = self._create_offer(
            user, offer_type, f'MATCH_ADD_{offer_type.replace(" ", "_")}',
            lead_entity_ids=[village.id],
        )
        unrestricted = self._create_offer(
            user, offer_type, f'FREE_ADD_{offer_type.replace(" ", "_")}',
        )
        flush()

        lead_matching = AddLeadService.add_lead(
            self._lead_base_data(
                user, village, matching.id, phone=self._unique_phone(1777000000 + matching.id)
            ),
            user,
        )
        assert lead_matching.offer.id == matching.id

        lead_free = AddLeadService.add_lead(
            self._lead_base_data(
                user, village, unrestricted.id, phone=self._unique_phone(1666000000 + unrestricted.id)
            ),
            user,
        )
        assert lead_free.offer.id == unrestricted.id

    @db_session
    def test_edit_lead_rejects_restricted_offer(self):
        user = UserGetterService.get_by_username('super_admin@test.com')
        village = OperationalEntitiesGetterService.get_list(user, level=0).first()
        other_village = EditOperationalEntityService.add_from_data_and_user({
            'name': 'Other Village EditLead',
            'level': 0,
            'parent_id': village.parent.id,
        }, user)
        flush()

        lead = ClientCreator.create_lead(offer_data={'code': 'BASE_EDIT_RESTRICT'})
        restricted = self._create_offer(
            user, 'Loan', 'RESTR_EDIT_OFFER',
            lead_entity_ids=[other_village.id],
        )
        flush()
        with pytest.raises(Error) as error:
            EditLeadService.edit_lead(lead, {'offer': restricted.id}, user)
        assert error.value.code == 'OFFER_NOT_AVAILABLE_IN_ENTITY'

    @db_session
    def test_edit_lead_allows_matching_offer(self):
        user = UserGetterService.get_by_username('super_admin@test.com')
        village = OperationalEntitiesGetterService.get_list(user, level=0).first()
        lead = ClientCreator.create_lead(offer_data={'code': 'BASE_EDIT_MATCH'})
        matching = self._create_offer(
            user, 'Loan', 'MATCH_EDIT_OFFER', lead_entity_ids=[village.id]
        )
        flush()
        EditLeadService.edit_lead(lead, {'offer': matching.id}, user)
        assert lead.offer.id == matching.id
