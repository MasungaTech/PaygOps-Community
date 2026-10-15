from flask import jsonify

from shared.helpers.date_helper import DateDifferenceService
from shared.helpers.week_helper import WeekService


class ChartResponse:
    COLORS = {
        0: 'rgba(153,255,51,0.4)',
        1: 'rgba(255,153,0,0.4)',
        2: 'rgba(216,60,51,0.4)',
        3: 'rgba(255, 0, 0, 0.4)',
        4: 'rgba(100, 30, 0, 0.4)',
    }

    def __init__(self, type, labels, data=[]):
        self.data = data
        self.labels = labels
        self.type = type

    def to_json(self):
        return jsonify({
            'success': True,
            'data': {
                'labels': self.data['labels'],
                'datasets': self.data['datasets']
            },
            'type': self.type,
        })


class ChartService:
    @staticmethod
    def generate_response(data, percentage=False, label_name=None):
        index = 0
        response = {
            'labels': data.labels,
            'datasets': []
        }
        if hasattr(data, 'chart_values'):
            for key, info in data.chart_values.items():
                response.get('datasets').append({
                    'label': key,
                    'data': info.get_values(percentage=percentage,
                                            total=data.total),
                    'value': info.values,
                    'percentage': info.values,
                    'backgroundColor': ChartResponse.COLORS.get(index),
                })

                index += 1
        else:
            response.get('datasets').append({
                'label': label_name if label_name is not None else 'Dropped Clients',
                'data': data.get_values(percentage=percentage),
                'value': data.values,
                'percentage': data.values,
                'backgroundColor': ChartResponse.COLORS.get(index),
            })

        response['datasets'] = sorted(response['datasets'], key=lambda d: d['label'])
        chart = ChartResponse(type='line', labels=data.labels, data=response)

        return chart.to_json()


class GroupedLabels():
    def __init__(self, labels):
        self.labels = labels
        self.chart_values = {}
        self.total = [0 for l in labels]

    def append(self, key, index, value=1):
        if key not in self.chart_values:
            self.chart_values[key] = ChartValues(self.labels)

        index = self.chart_values.get(key).append_in_values(index, value=value)
        if index is not None:
            self.total[index] += value


class ChartValues:
    def __init__(self, labels):
        self.labels = labels
        self.values = []
        self.positions = {}
        self.label_values = {}
        for i, l in enumerate(labels):
            self.values.append(0)
            self.label_values[l] = []
            self.positions[l] = i

    def fix_values(self, label, value):
        index = self.append_in_values(label)
        if index is not None:
            self.values[index] = value

    def append_in_values(self, label, value=1):
        index = self.positions.get(label)
        if index is not None:
            self.values[index] += value
        return index

    def append_for_average(self, label, value):
        if label not in self.label_values:
            self.label_values[label] = []
        self.label_values[label].append(value)

    def calculate_averages(self):
        for label in self.labels:
            total = 0
            for val in self.label_values[label]:
                total += val
            index = self.positions.get(label)
            if index is not None:
                self.values[index] = round(total/len(self.label_values[label]), 2) if len(self.label_values[label]) > 0 else 0

    def get_values(self, percentage=False, total=[]):
        percent_values = [0 for t in total]

        if percentage and len(total) == len(self.values):
            for index, value in enumerate(self.values):
                if value > 0 and total[index] > 0:
                    percent = (value / total[index]) * 100
                    percent_values[index] = percent

            return percent_values

        return self.values


class MonthlyGraphPointsService:
    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date
        self.data = []

    @property
    def total_time(self):
        return DateDifferenceService.monthly_diff(self.end_date, self.start_date) + 1

    @property
    def time_passed(self):
        return DateDifferenceService.monthly_diff(WeekService.get_weekly_date(1), self.end_date)

    def from_date(self, n):
        return DateDifferenceService.get_monthly_date(self.total_time - n + self.time_passed + 1)

    def to_date(self, n):
        return DateDifferenceService.get_monthly_date(self.total_time - 1 - n + self.time_passed + 1)

    def generate_graph_points(self, y_func):
        for n in range(self.total_time):
            x_value = DateDifferenceService.get_monthly_date(self.total_time - n + self.time_passed + 1).strftime(
                "%b %Y")

            y_value = y_func(self.from_date(n), self.to_date(n))

            self.data.append((x_value, y_value))
        return self.data


class WeeklyGraphPointsService:
    def __init__(self, start_date, end_date):
        self.start_date = start_date.date()
        self.end_date = end_date.date()
        self.data = []

    @property
    def total_time(self):
        diff = DateDifferenceService.get_weekly_difference(self.start_date, self.end_date)
        return diff + 1

    @property
    def time_passed(self):
        return DateDifferenceService.get_weekly_difference(WeekService.get_weekly_date(), self.end_date)

    def from_date(self, n):
        return WeekService.get_weekly_date(self.total_time - n + self.time_passed + 1)

    def to_date(self, n):
        return WeekService.get_weekly_date(self.total_time - 1 - n + self.time_passed + 1)

    def generate_graph_points(self, y_func):
        for n in range(self.total_time):
            x_value = WeekService.get_weekly_date(self.total_time - n + self.time_passed + 1).strftime(
                "%d %b %Y")
            y_value = y_func(self.from_date(n), self.to_date(n))

            self.data.append((x_value, y_value))
        return self.data


class DailyGraphPointsService:
    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date
        self.data = []

    @property
    def total_time(self):
        return DateDifferenceService.number_of_days_in_between(self.start_date, self.end_date) - 1

    @property
    def time_passed(self):
        return DateDifferenceService.number_of_days_in_between(WeekService.get_weekly_date(), self.end_date)

    def from_date(self, n):
        return list(DateDifferenceService.daily_difference(self.start_date, self.end_date))[n]

    def to_date(self, n):
        return list(DateDifferenceService.daily_difference(self.start_date, self.end_date))[n + 1]

    def generate_graph_points(self, y_func):

        for n in range(self.total_time):
            if n >= self.total_time:
                break
            x_value = self.from_date(n)
            y_value = y_func(self.from_date(n), self.to_date(n))

            self.data.append((x_value.strftime("%d %b %Y"), y_value))
        return self.data
