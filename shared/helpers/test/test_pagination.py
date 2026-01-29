import pytest
from shared.helpers.pagination import ResultSet, Pagination
import mock
from munch import Munch


@pytest.fixture
def elements():
    return [x for x in range(100)]


@pytest.fixture
def resultset(elements):
    return ResultSet(elements)


@pytest.fixture
def pagination(resultset):
    return Pagination(1, 10, resultset)


class TestResultSet:
    def test_resultset_len(self, elements, resultset):
        assert len(elements) == resultset.count()

    def test_resultset_page_with_invalid_page(self, resultset):
        assert [] == resultset.page(50, 100)

    def test_resultset_page_with_greater_per_page(self, elements):
        resultset = ResultSet(elements)

        assert elements == resultset.page(1, 200)

    def test_resultset_page_with_page_and_per_page_zero(self, resultset):
        assert [] == resultset.page(0, 0)

    def test_resultset_page_with_page_and_per_page_none(self, resultset):
        assert [] == resultset.page(None, None)


class TestPagination:

    def test_constructor(self, pagination):
        assert 10 == pagination.pages
        assert pagination.has_next
        assert pagination.has_prev is False

    def test_url_params(self, pagination):
        assert "?page=1&per_page=10&tab=" == pagination.url_params(1, 10)

    def test_reverse_sort_url_asc(self, pagination):
        params = pagination.reverse_sort_url('Name:asc')
        assert "?page=1&per_page=10&tab=&sort=Name:desc" == params

    def test_reverse_sort_url_desc(self, pagination):
        params = pagination.reverse_sort_url('Name:desc')

        assert "?page=1&per_page=10&tab=&sort=Name:asc" == params

    def test_active_returns_empty_string(self, pagination):
        assert "" == pagination.active(2)

    def test_active_returns_active(self, pagination):
        assert "active" == pagination.active(1)

    def test_sortable_returns_empty_string(self, pagination):
        assert "" == pagination.sortable()

    def test_sortable_returns_sortable(self, resultset):
        pagination = Pagination(1, 100, resultset)
        assert "sortable" == pagination.sortable()

    def test_iter_pages(self, resultset):
        pagination = Pagination(1, 2, resultset)
        pages = [x for x in pagination.iter_pages()]

        assert 8 == len(pages)

        assert 1 == pages[0]
        assert 2 == pages[1]
        assert 3 == pages[2]
        assert 4 == pages[3]
        assert 5 == pages[4]
        assert pages[5] is None
        assert 49 == pages[6]
        assert 50 == pages[7]

    def test_in_between_left_side_returns_false(self, resultset):
        pagination = Pagination(10, 2, resultset)
        assert pagination.in_between(2, 5, 20) is False

    def test_in_between_right_side_returns_false(self, resultset):
        pagination = Pagination(10, 2, resultset)
        assert pagination.in_between(20, 5, 10) is False

    def test_in_between_returns_true(self, pagination):
        assert pagination.in_between(2, 5, 5)

    def test_generate_pagination_with_get_request(self):
        mock_request = Munch()
        mock_request.method = 'GET'
        mock_request.form = {}
        mock_request.args = {
            'page': 2,
            'per_page': 15,
            'sort': 'id:asc',
            'search': 'test'}

        pagination = Pagination.generate(mock_request)

        assert mock_request.args.get('page') == pagination.page
        assert mock_request.args.get('per_page') == pagination.per_page
        assert mock_request.args.get('sort') == pagination.sort
        assert mock_request.args.get('search') == pagination.search

    def test_generate_pagination_with_post_request(self):
        mock_request = Munch()
        mock_request.method = 'POST'
        mock_request.form = {'search': 'test_form'}
        mock_request.args = {
            'page': 2,
            'per_page': 15,
            'sort': 'id:asc',
            'search': 'test'}

        pagination = Pagination.generate(mock_request)

        assert 1 == pagination.page
        assert Pagination.PER_PAGE == pagination.per_page
        assert mock_request.args.get('sort') == pagination.sort
        assert mock_request.form.get('search') == pagination.search

    def test_set_objects(self):
        mock_request = Munch()
        mock_request.method = 'POST'
        mock_request.form = {'search': 'test_form'}
        mock_request.args = {
            'page': 2,
            'per_page': 15,
            'sort': 'id:asc',
            'search': 'test'}

        pagination = Pagination.generate(mock_request)
        pagination.objects = ResultSet([])

        assert pagination.total_count == 0
