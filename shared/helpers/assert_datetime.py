from datetime import timedelta


def assert_datetime(d1, d2, **kwargs):
    if not kwargs:
        kwargs['seconds'] = 1
    diff = abs(d1-d2)
    threshold = timedelta(**kwargs)
    assert diff < threshold, f'Datetimes difference is {diff}, over the {threshold} threshold'
