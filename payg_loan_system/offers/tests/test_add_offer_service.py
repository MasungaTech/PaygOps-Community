import pytest
from pony.orm import db_session, flush

from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from payg_loan_system.offers.services.create_offer_service import CreateOfferService

# TO DO: test with different values for parameters (invalid ones mainly)
class TestCreateOfferService:

    ENTITY_RESTRICTION_COMMON_FIELDS = {
        'family': 'Home',
        'can_be_approved_and_registered': True,
        'in_use_for_new_leads': True,
        'approval_required': False,
        'device_type': 'NPG',
        'raw_unit_cost': 2000,
        'lighting_global_compliant': True,
    }

    @staticmethod
    def _entity_ids_for_user(user, count=2):
        entities = OperationalEntitiesGetterService.get_list(user, only_hierarchical=True)
        return [e.id for e in entities[:count]]

    @db_session
    def test_create_offer_loan(self, super_admin_user):

        data = {
            'name': 'TEST_CREATE_SERVICE_LOAN',
            'code': 'TEST_CREATE_SERVICE_LOAN',
            'type': 'Loan',
            'time_to_ownership_in_days': 365,
            'downpayment': 30,
            'time_given_at_start_in_days': 5,
            'base_price_amount': 5,
            'base_price_time_in_days': 1,
            'discount_price_1_amount': 6,
            'discount_price_1_time_in_days': 2,
            'family': 'Home',
            'can_be_approved_and_registered': True,
            'in_use_for_new_leads': False,
            'approval_required': False,
            'device_type': 'NPG',
            'raw_unit_cost': 2000,
            'lighting_global_compliant': True
        }
        offer = CreateOfferService.add_from_data_and_user(data, super_admin_user())
        flush()
        for k in data:
            assert data[k] == offer.get_serialized_object()[k]

    @db_session
    def test_create_offer_lump(self, super_admin_user):

        data = {
            'name': 'TEST_CREATE_SERVICE_LUMP',
            'code': 'TEST_CREATE_SERVICE_LUMP',
            'type': 'Lump Sum',
            'base_price_amount_lump_sum': 5,
            'family': 'Home',
            'can_be_approved_and_registered': True,
            'in_use_for_new_leads': False,
            'approval_required': False,
            'device_type': 'NPG',
            'raw_unit_cost': 2000,
            'lighting_global_compliant': True
        }
        offer = CreateOfferService.add_from_data_and_user(data, super_admin_user())
        flush()
        for k in data:
            assert data[k] == offer.get_serialized_object()[k]

    @db_session
    def test_create_offer_time(self, super_admin_user):

        data = {
            'name': 'TEST_CREATE_SERVICE_TIME',
            'code': 'TEST_CREATE_SERVICE_TIME',
            'type': 'Time Based',
            'downpayment': 30,
            'time_given_at_start_in_days': 5,
            'base_price_amount': 5,
            'base_price_time_in_days': 1,
            'family': 'Home',
            'can_be_approved_and_registered': True,
            'in_use_for_new_leads': False,
            'approval_required': True,
            'device_type': 'NPG',
            'raw_unit_cost': 2000,
            'lighting_global_compliant': True
        }
        offer = CreateOfferService.add_from_data_and_user(data, super_admin_user())
        flush()
        for k in data:
            assert data[k] == offer.get_serialized_object()[k]

    @db_session
    @pytest.mark.parametrize('offer_type,extra_fields,code_suffix', [
        ('Loan', {
            'time_to_ownership_in_days': 365,
            'downpayment': 30,
            'time_given_at_start_in_days': 5,
            'base_price_amount': 5,
            'base_price_time_in_days': 1,
            'discount_price_1_amount': 6,
            'discount_price_1_time_in_days': 2,
        }, 'LOAN'),
        ('Lump Sum', {
            'base_price_amount_lump_sum': 5,
        }, 'LUMP'),
    ])
    @pytest.mark.parametrize('entity_id_style', ['legacy', 'add'])
    def test_create_offer_saves_entity_restrictions(
        self, super_admin_user, offer_type, extra_fields, code_suffix, entity_id_style,
    ):
        user = super_admin_user()
        lead_id, contract_id = self._entity_ids_for_user(user)
        if entity_id_style == 'legacy':
            entity_fields = {
                'entities_allowed_for_leads_ids': [lead_id],
                'entities_allowed_for_contracts_ids': [contract_id],
            }
        else:
            entity_fields = {
                'add_entities_allowed_for_leads_ids': [lead_id],
                'add_entities_allowed_for_contracts_ids': [contract_id],
            }

        offer = CreateOfferService.add_from_data_and_user({
            'name': f'TEST_ENTITIES_{code_suffix}_{entity_id_style}',
            'code': f'TEST_ENTITIES_{code_suffix}_{entity_id_style}',
            'type': offer_type,
            **self.ENTITY_RESTRICTION_COMMON_FIELDS,
            **extra_fields,
            **entity_fields,
        }, user)
        flush()

        assert [e.id for e in offer.entities_allowed_for_leads] == [lead_id]
        assert [e.id for e in offer.entities_allowed_for_contracts] == [contract_id]

        serialized = offer.get_serialized_object()
        assert serialized['entities_allowed_for_leads_ids'] == [lead_id]
        assert serialized['entities_allowed_for_contracts_ids'] == [contract_id]

    @db_session
    def test_create_offer_prefers_add_entity_ids_over_legacy(self, super_admin_user):
        user = super_admin_user()
        lead_id, contract_id, other_lead_id = self._entity_ids_for_user(user, count=3)

        offer = CreateOfferService.add_from_data_and_user({
            'name': 'TEST_ENTITIES_PREFER_ADD',
            'code': 'TEST_ENTITIES_PREFER_ADD',
            'type': 'Loan',
            'time_to_ownership_in_days': 365,
            'downpayment': 30,
            'time_given_at_start_in_days': 5,
            'base_price_amount': 5,
            'base_price_time_in_days': 1,
            'discount_price_1_amount': 6,
            'discount_price_1_time_in_days': 2,
            **self.ENTITY_RESTRICTION_COMMON_FIELDS,
            'entities_allowed_for_leads_ids': [lead_id],
            'add_entities_allowed_for_leads_ids': [other_lead_id],
            'entities_allowed_for_contracts_ids': [lead_id],
            'add_entities_allowed_for_contracts_ids': [contract_id],
        }, user)
        flush()

        assert [e.id for e in offer.entities_allowed_for_leads] == [other_lead_id]
        assert [e.id for e in offer.entities_allowed_for_contracts] == [contract_id]
