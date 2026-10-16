from datetime import datetime, timedelta
from shared.helpers.list_helpers import timePeriodHelper


def test_time_period_helper():
    cases = ['7', '14', '30', '90', 'forever']
    default = 14
    now = datetime.now()

    for case in cases:
        if case == 'forever':
            assert timePeriodHelper(case, default) == datetime.min
        else:
            assert timePeriodHelper(case, default).replace(microsecond=0) == (now - timedelta(days=int(case))).replace(
                microsecond=0)

    assert timePeriodHelper('20', default).replace(microsecond=0) == (now - timedelta(days=default)).replace(
        microsecond=0)
