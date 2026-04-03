from pony.orm import db_session, flush
from payg_loan_system.offers.services.create_offer_service import CreateOfferService

# TO DO: test with different values for parameters (invalid ones mainly)
class TestCreateOfferService:

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
