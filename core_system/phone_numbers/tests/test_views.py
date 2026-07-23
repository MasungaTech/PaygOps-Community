from pony.orm import db_session
from tests.base_test import BaseViewTest


class TestPhoneNumberList(BaseViewTest):
    url = 'phone_numbers.search_phone_numbers'
    template = 'search.html'