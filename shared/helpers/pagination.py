from math import ceil


class ResultSet:
    def __init__(self, resultset):
        self.resultset = resultset

    def page(self, page, per_page):
        if type(page) is int and type(per_page) is int:
            first = self._index(page, per_page)
            last = self._last_index(page, per_page)

            return self.resultset[first:last]

        return []

    def _index(self, page, per_page):
        return (page * per_page) - per_page

    def _last_index(self, page, per_page):
        return page * per_page

    def count(self):
        return len(self.resultset)


class Pagination:
    PER_PAGE = 10
    endpoint = ''

    def __init__(self,
                 page,
                 per_page,
                 resultset,
                 sort="Name:asc",
                 search='',
                 params='',
                 tab=''):
        self.page = page
        self.per_page = per_page
        self.sort = sort
        self.search = search
        self.resultset = resultset
        self.params = params
        self.tab = tab
        self.page_objects = self.resultset.page(self.page, self.per_page)
        self.total_count = self.resultset.count()

    @staticmethod
    def generate(this_request, params='', tab='', default_sort='id:asc', per_page=None):

        sort = default_sort
        page = 1
        per_page = per_page if per_page else Pagination.PER_PAGE
        search = this_request.form.get('search', this_request.args.get('search', ''))

        if this_request.method == 'GET' and this_request.args.get('tab', '') == tab:
            page = int(this_request.args.get('page', 1))
            per_page = int(this_request.args.get('per_page', per_page if per_page else Pagination.PER_PAGE))
            sort = this_request.args.get('sort', default_sort)

        return Pagination(
            page,
            per_page,
            ResultSet([]),
            sort=sort,
            search=search,
            params=params,
            tab=tab
        )

    @property
    def pages(self):
        if not self.is_empty:
            return int(ceil(self.total_count / float(self.per_page)))
        return 0

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def objects(self):
        return self.page_objects

    @objects.setter
    def objects(self, resultset):
        self.resultset = resultset
        self.page_objects = self.resultset.page(self.page, self.per_page)
        self.total_count = self.resultset.count()

    @property
    def is_empty(self):
        if self.resultset != []:
            return False
        return True

    def url_params(self, page, per_page=None):
        if not per_page:
            per_page = self.per_page

        return "?page={0}&per_page={1}{2}&tab={3}".format(
            page, per_page, self.get_params(), self.tab)

    def reverse_sort_url(self, sort, tab=""):
        sort_url = sort + tab
        self_sort_url = self.sort + tab
        pagination_params = self.url_params(self.page, self.per_page)
        if self.search:
            pagination_params = pagination_params + '&search=' + self.search
        if sort_url == self_sort_url:
            if "asc" in sort_url:
                return "{0}&sort={1}{2}".format(
                    pagination_params,
                    sort_url.replace(":asc", ":desc"),
                    self.get_params())

        return "{0}&sort={1}{2}".format(
            pagination_params,
            sort_url.replace(":desc", ":asc"),
            self.get_params())

    def active(self, page):
        status = ""
        if page == self.page:
            status = "active"

        return status

    def sortable(self):
        status = ""

        if self.all():
            status = "sortable"

        return status

    def has_pages(self):
        return self.pages > 1

    def all(self):
        if not self.is_empty:
            return self.per_page == self.total_count

    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=5, right_edge=2):
        last = 0
        for num in range(1, self.pages + 1):
            if num <= left_edge or \
               self.in_between(num, left_current, right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num

    def in_between(self, num, left_current, right_current):
        left_side = self.page - left_current - 1
        right_side = self.page + right_current

        return num > left_side and num < right_side

    def get_params(self):
        if self.params:
            return '&{}'.format(self.params)

        return ''


class NestedPagination(Pagination):
    def __init__(self, endpoint, *args, **kwargs):
        super(NestedPagination, self).__init__(*args, **kwargs)
        self.endpoint = endpoint