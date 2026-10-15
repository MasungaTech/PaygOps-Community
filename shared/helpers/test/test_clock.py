from shared.helpers.clock import Clock
import re


class TestClock:
    def test_it_tells_the_time_in_isoformat(self):
        iso_regexp = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3,}Z'
        result = Clock.now()

        assert re.match(iso_regexp, result)
