from decimal import Decimal
from pony.orm import db_session, flush
from payg_loan_system.offers.services.create_offer_service import CreateOfferService
from payg_loan_system.offers.services.edit_offer_service import EditOfferService
from shared.logger.loggers import Error


class BaseEditOfferServiceTest:

    INITIAL_DATA = {}
    BAD_CHANGES = {}
    GOOD_CHANGES = {}

    def setup_class(self):
        pass

    @db_session
    def test_edit_offer_with_config(self, super_admin_user):
        offer = CreateOfferService.add_from_data_and_user(self.INITIAL_DATA, super_admin_user())
        flush()
        for change in self.BAD_CHANGES:
            for val in self.BAD_CHANGES[change]:
                key = change
                if change == "time_given_at_start_in_days":
                    key = "free_credit_at_start"
                if change == "base_price_time_in_days":
                    key = "base_price_credit"
                if change == "discount_price_1_time_in_days":
                    key = "discount_price_1_credit"
                if change == "discount_price_2_time_in_days":
                    key = "discount_price_2_credit"
                try:
                    EditOfferService.edit_from_data_and_user(offer, {key: val}, super_admin_user())
                    flush()
                except (ValueError, TypeError, Error) as error:
                    EditOfferService.edit_from_data_and_user(offer, {key: self.INITIAL_DATA[change]}, super_admin_user())
                else:
                    org = offer.get_serialized_object()[change]
                    print("Offer: "+str(offer.get_serialized_object()))
                    print("BAD CHANGES: "+str(self.BAD_CHANGES))
                    print("Change: "+str(change)+" Val: "+str(val)+" Org: "+str(org))
                    self.assert_value(org, val, equal=False)
                    raise Exception('Did not raise exception', change, val)

        for change in self.GOOD_CHANGES:
            for val in self.GOOD_CHANGES[change]:
                key = change
                if change == "time_given_at_start_in_days":
                    key = "free_credit_at_start"
                if change == "base_price_time_in_days":
                    key = "base_price_credit"
                if change == "discount_price_1_time_in_days":
                    key = "discount_price_1_credit"
                if change == "discount_price_2_time_in_days":
                    key = "discount_price_2_credit"
                try:
                    EditOfferService.edit_from_data_and_user(offer, {key: val}, super_admin_user())
                    flush()
                except Exception as error:
                    raise Exception(f'Good change failed: {change} with value {val}. Details: {str(error)}')
                org = offer.get_serialized_object()[change]
                self.assert_value(org, val)

    @staticmethod
    def assert_value(org, val, equal=True):
        if isinstance(org, Decimal) or isinstance(org, float):
            assert (equal and org == Decimal(val)) or (not equal and org != Decimal(val))
        elif isinstance(org, int):
            assert (equal and org == int(Decimal(val))) or (not equal and org != int(Decimal(val)))
        else:
            assert (equal and org == val) or (not equal and org != val)
