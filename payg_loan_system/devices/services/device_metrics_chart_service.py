from datetime import datetime
from shared.helpers.chart import ChartService, ChartValues
from shared.helpers.date_helper import interval_dates, get_index_by_date_frequency, \
    DateDifferenceService
from payg_loan_system.devices.model.device_metrics_model import MetricType

class DeviceLineChartService:
    def __init__(self, device):
        self.device = device

    def usage_metric_info(self, start_date, end_date, metric):
        metric_type = MetricType.get(uuid=metric)
        info = self.generate_metrics_data(self.device,
                                          start_date,
                                          end_date,
                                          metric_type)
        metric_name = getattr(metric_type, 'name')
        return ChartService.generate_response(info, label_name=metric_name)

    def generate_metrics_data(self,
                              device,
                              start_date,
                              end_date,
                              metric_type):

        frequency = self.get_frequency(start_date, end_date)
        labels = interval_dates(start_date, end_date, frequency)
        metrics = device.get_usage_metrics_by_date(start_date, end_date, metric_type)
        group = ChartValues(labels)

        for metric in metrics:
            if frequency == '6h':
                metric_time = metric.time
                #get appropriate date from labels so that metrics are grouped appropriately
                for label in labels:
                    date = datetime.strptime(label, '%Y-%m-%d %H:%M:%S')
                    if date >= metric.time:
                        metric_time = date
                        break
                index = get_index_by_date_frequency(metric_time, frequency='h')
            else:
                index = get_index_by_date_frequency(metric.time, frequency=frequency)

            key = metric.value
            group.append_for_average(index, key)
        group.calculate_averages()
        return group

    def get_frequency(self, start_date, end_date):
        diff = end_date - start_date
        month_diff = DateDifferenceService.monthly_diff(end_date, start_date)
        year_diff = end_date.year - start_date.year
        if diff.days <= 2:
            return 'h'
        elif diff.days <= 30:
            return '6h'
        elif month_diff <= 3:
            return 'd'
        elif year_diff <= 1:
            return 'w'
        else:
            return 'y'
