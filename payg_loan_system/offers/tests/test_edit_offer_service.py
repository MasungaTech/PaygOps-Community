from payg_loan_system.offers.tests.base_test_edit_offer_service import BaseEditOfferServiceTest


class TestEditOfferServiceLoan(BaseEditOfferServiceTest):

    INITIAL_DATA = {
        'name': 'TEST_EDIT_SERVICE_LOAN',
        'code': 'TEST_EDIT_SERVICE_LOAN',
        'type': 'Loan',
        'time_to_ownership_in_days': 365,
        'downpayment': 30.0,
        'time_given_at_start_in_days': 5,
        'base_price_amount': 5,
        'base_price_time_in_days': 1,
        'discount_price_1_amount': 10,
        'discount_price_1_time_in_days': 3,
        'discount_price_2_amount': 20,
        'discount_price_2_time_in_days': 7,
        'family': 'Home',
    }

    BAD_CHANGES = {
        'name': [1, None, '', {}, []],
        'code': [1, None, '', {}, []],
        'time_to_ownership_in_days': [None, '', {}, [], 'sdfsad'],
        'downpayment': [None, '', {}, [], 'sdfsad'],
        'time_given_at_start_in_days': [None, '', {}, [], 'sdfsad'],
        'base_price_amount': [None, '', {}, [], 'sdfsad'],
        'base_price_time_in_days': [None, '', {}, [], 'sdfsad'],
        'discount_price_1_amount': [None, '', {}, [], 'sdfsad', 1, 2, 3, 4], 
        # None is not valid cause we have a discount 2
        'discount_price_1_time_in_days': [None, '', {}, [], 'sdfsad'],
        'discount_price_2_amount': ['sdfsad', 1, 3, 5, 7, 9], #empty values are valid cause is optional
        'discount_price_2_time_in_days': [None, '', {}, [], 'sdfsad'],
        'family': [None, '', {}, [], 'sdfsad'],
    }

    GOOD_CHANGES = {
        'name': ['TEST_EDIT_SERVICE_LOAN_CHANGED', '1234'],
        'code': ['TEST_EDIT_SERVICE_LOAN_CHANGED', '1234'],
        'time_to_ownership_in_days': ['100', 100],
        'downpayment': ['100', 100],
        'time_given_at_start_in_days': ['10', 10],
        'base_price_amount': ['10', 10],
        'base_price_time_in_days': ['1', 1],
        'discount_price_2_amount': ['10', 10, None],
        'discount_price_2_time_in_days': ['1', 1, None],
        'discount_price_1_amount': ['10', 10, None],
        'discount_price_1_time_in_days': ['1', 1, None],
        'family': ['Home', 'Business']
    }


class TestEditOfferServiceTime(BaseEditOfferServiceTest):

    INITIAL_DATA = {
        'name': 'TEST_EDIT_SERVICE_TIME',
        'code': 'TEST_EDIT_SERVICE_TIME',
        'type': 'Time Based',
        'downpayment': 30,
        'time_given_at_start_in_days': 5,
        'base_price_amount': 5,
        'base_price_time_in_days': 1,
        'discount_price_1_amount': 10,
        'discount_price_1_time_in_days': 3,
        'discount_price_2_amount': 20,
        'discount_price_2_time_in_days': 7,
        'family': 'Home'
    }

    BAD_CHANGES = {
        'name': [1, None, '', {}, []],
        'code': [1, None, '', {}, []],
        'downpayment': [None, '', {}, [], 'sdfsad'],
        'time_given_at_start_in_days': [None, '', {}, [], 'sdfsad'],
        'base_price_amount': [None, '', {}, [], 'sdfsad'],
        'base_price_time_in_days': [None, '', {}, [], 'sdfsad'],
        'discount_price_1_amount': [None, '', {}, [], 'sdfsad', 1, 2, 3, 4], 
        # None is not valid cause we have a discount 2
        'discount_price_1_time_in_days': [None, '', {}, [], 'sdfsad'],
        'discount_price_2_amount': ['sdfsad', 1, 3, 5, 7, 9], #empty values are valid cause is optional
        'discount_price_2_time_in_days': [None, '', {}, [], 'sdfsad'],
        'family': [None, '', {}, [], 'sdfsad']
    }

    GOOD_CHANGES = {
        'name': ['TEST_EDIT_SERVICE_TIME_CHANGED', '4321'],
        'code': ['TEST_EDIT_SERVICE_TIME_CHANGED', '4321'],
        'downpayment': ['100', 100],
        'time_given_at_start_in_days': ['10', 10],
        'base_price_amount': ['10', 10],
        'base_price_time_in_days': ['1', 1],
        'discount_price_2_amount': ['10', 10, None],
        'discount_price_2_time_in_days': ['1', 1, None],
        'discount_price_1_amount': ['10', 10, None],
        'discount_price_1_time_in_days': ['1', 1, None],
        'family': ['Home', 'Business']
    }


class TestEditOfferServiceLump(BaseEditOfferServiceTest):

    INITIAL_DATA = {
        'name': 'TEST_EDIT_SERVICE_LUMP',
        'code': 'TEST_EDIT_SERVICE_LUMP',
        'type': 'Lump Sum',
        'base_price_amount_lump_sum': 500,
        'family': 'Home',
    }

    BAD_CHANGES = {
        'name': [1, None, '', {}, []],
        'code': [1, None, '', {}, []],
        'base_price_amount_lump_sum': [None, '', {}, [], 'sdfsad'],
        'family': [None, '', {}, [], 'sdfsad'],
    }

    GOOD_CHANGES = {
        'name': ['TEST_EDIT_SERVICE_LUMP_CHANGED', '1221'],
        'code': ['TEST_EDIT_SERVICE_LUMP_CHANGED', '2112'],
        'base_price_amount_lump_sum': ['10', 10],
        'family': ['Home', 'Business']
    }
