import pytest
from shared.helpers.chart import ChartValues, GroupedLabels


class TestGroupedLabels:
    @pytest.fixture
    def labels(self):
        return ['Pos 0', 'Pos 1', 'Pos 2']

    def test_constructor(self, labels):
        group = GroupedLabels(labels)

        assert labels == group.labels
        assert [0, 0, 0] == group.total
        assert {} == group.chart_values

    def test_append(self, labels):
        group = GroupedLabels(labels)

        group.append('one', labels[0])
        group.append('two', labels[0])
        group.append('two', labels[1])

        assert [2, 1, 0] == group.total
        assert 'one' in list(group.chart_values.keys())
        assert 'two' in list(group.chart_values.keys())
        assert [1, 0, 0] == group.chart_values.get('one').values
        assert [1, 1, 0] == group.chart_values.get('two').values

class TestChartValues:
    @pytest.fixture
    def labels(self):
        return ['Pos 0', 'Pos 1', 'Pos 2']

    def test_constructor(self, labels):
        chart_values = ChartValues(labels)

        assert len(labels) == len(chart_values.values)
        assert len(labels) == len(chart_values.positions)
        assert {
            labels[0]: 0,
            labels[1]: 1,
            labels[2]: 2
        } == chart_values.positions

    def test_append_in_values(self, labels):
        chart_values = ChartValues(labels)

        index_one = chart_values.append_in_values(labels[0])

        chart_values.append_in_values(labels[1])
        index_two = chart_values.append_in_values(labels[1])

        chart_values.append_in_values(labels[2])
        chart_values.append_in_values(labels[2])
        index_three = chart_values.append_in_values(labels[2])

        assert 0 == index_one
        assert 1 == index_two
        assert 2 == index_three

        assert 1 == chart_values.values[0]
        assert 2 == chart_values.values[1]
        assert 3 == chart_values.values[2]

    def test_get_values(self, labels):
        chart_values = ChartValues(labels)

        chart_values.append_in_values(labels[0])
        chart_values.append_in_values(labels[1])
        chart_values.append_in_values(labels[1])
        chart_values.append_in_values(labels[2])
        chart_values.append_in_values(labels[2])
        chart_values.append_in_values(labels[2])

        assert [1, 2, 3] == chart_values.get_values(False, [])
        assert [1, 2, 3] == chart_values.get_values(True, [])
        assert [10, 20, 30] == chart_values.get_values(percentage=True,
                                                       total=[10, 10, 10])
