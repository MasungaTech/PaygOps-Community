from tests.base_test import BaseViewTest


class TestDirectRequestView(BaseViewTest):
    url = 'mentor_request.direct_request'
    template = 'manual_request.html'


class TestListMentorRequestsView(BaseViewTest):
    url = 'mentor_request.list_request'
    template = 'user_requests.html'


class TestListActivationRequests(BaseViewTest):
    url = 'mentor_request.token_list'
    template = 'token_list.html'

