from api_app.tests.base_api_test import BaseAPITest


class TestOfferAPILoan(BaseAPITest):
    BASE_URL = '/offers'
    SAMPLE_DATA = {
        "type": "Loan",
        "name": "My Super Offer 1",
        "code": "MSO1",
        "family": "Home",
        "can_be_approved_and_registered": True,
        "in_use_for_new_leads": True,
        "approval_required": True,
        "automatic_unlock_code_sending": False,
        "downpayment": 75000,
        "time_to_ownership_in_days": 756,
        "time_given_at_start_in_days": 28,
        "base_price_amount": 8700,
        "base_price_time_in_days": 7,
        "discount_price_1_amount": 34800,
        "discount_price_1_time_in_days": 32,
        "discount_price_2_amount": None,
        "discount_price_2_time_in_days": None,
        "device_type": "SOL",
        "raw_unit_cost": 500000,
        "lighting_global_compliant": True,
        "panel_size_in_w": 40,
        "battery_size_in_ah": 22,
        "maximum_value_extension": None,
        "allow_loan_addons": True,
        "notes": '',
        "base_price_amount_can_be_negative": False
    }
    RESPONSE_DATA = {
        "allowed_addon_offer_categories_ids": [],
        'allow_pro_rata': True,
        'forgive_lateness': True,
        'linked_to_product': False,
    }
    EDIT_DATA = {
        'name': 'My Genial Offer',
        'code': 'MSO1A'
    }

class TestOfferAPITime(BaseAPITest):
    BASE_URL = '/offers'
    SAMPLE_DATA = {
        "type": "Time Based",
        "name": "My Super Offer 1",
        "code": "MSO2",
        "family": "Home",
        "can_be_approved_and_registered": True,
        "in_use_for_new_leads": True,
        "approval_required": True,
        "downpayment": 75000,
        "time_given_at_start_in_days": 28,
        "base_price_amount": 8700,
        "base_price_time_in_days": 7,
        "discount_price_1_amount": 34800,
        "discount_price_1_time_in_days": 32,
        "discount_price_2_amount": None,
        "discount_price_2_time_in_days": None,
        "device_type": "SOL",
        "raw_unit_cost": 500000,
        "lighting_global_compliant": True,
        "panel_size_in_w": 40,
        "notes": '',
        "payment_frequency": 'DAILY',
        "battery_size_in_ah": 22
    }
    
    RESPONSE_DATA = {
        "allowed_addon_offer_categories_ids": [],
        'allow_pro_rata': True,
        'forgive_lateness': True,
        'linked_to_product': False,
    }
    EDIT_DATA = {
        'name': 'My Genial Offer',
        'code': 'MSO2A'
    }

class TestOfferAPILump(BaseAPITest):
    BASE_URL = '/offers'
    SAMPLE_DATA = {
        "type": "Lump Sum",
        "name": "My Super Offer 1",
        "code": "MSO3",
        "family": "Home",
        "can_be_approved_and_registered": True,
        "in_use_for_new_leads": True,
        "approval_required": True,
        "base_price_amount_lump_sum": 8700,
        "device_type": "SOL",
        "raw_unit_cost": 500000,
        "lighting_global_compliant": True,
        "panel_size_in_w": 40,
        "notes": '',
        "battery_size_in_ah": 22,
        "base_price_amount_can_be_negative": False
    }
    RESPONSE_DATA = {
        "allowed_addon_offer_categories_ids": [],
        'linked_to_product': False,
    }
    EDIT_DATA = {
        'name': 'My Genial Offer',
        'code': 'MSO3A'
    }
