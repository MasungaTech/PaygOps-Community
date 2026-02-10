from tests.base_test import BaseViewTest


class TestListMessages(BaseViewTest):
    url = 'message.list_message'
    template = 'list_messages.html'
