from pony import orm
from datetime import datetime
from pony.orm import db_session
from config import NON_PAYG_TYPE
from payg_loan_system.devices.device_api.device_api_service import DeviceAPIService
from payg_loan_system.devices.model.device_metrics_model import MetricType, Metric
from payg_loan_system.devices.device_list_service import DeviceListService
from shared.services.base_getter_service import BaseGetterService


class DeviceMetricsService(BaseGetterService):

    OBJ_NAME = 'DeviceMetric'

    @classmethod
    def get_filtered_objects(cls, current_user, device_serial_number=None, name=None, **kwargs):
        metrics = Metric.select()
        if device_serial_number:
            metrics = metrics.filter(lambda m: m.device.composed_serial == device_serial_number)
        if name:
            metrics = metrics.filter(lambda m: m.metric_type.name == name)
        return metrics

    @classmethod
    def get_device_metric_types(cls, device, force_sync=False):
        raw_metric_types = DeviceAPIService.get_usage_metric_types_for_device(device, force_sync=force_sync)
        metric_types = []
        for data in raw_metric_types:
            uuid = data.get("uuid")
            name = data.get("name")
            credit_unit = data.get("unit") or "-" # to be change, nothing to do with credit
            format = data.get("format")
            metric_type = MetricType.get(uuid=uuid)
            if metric_type:
                metric_type.name = name
                metric_type.credit_unit = credit_unit
                metric_type.format = format
            else:
                metric_type = MetricType(
                    uuid=uuid,
                    name=name,
                    credit_unit=credit_unit,
                    format=format
                )
            metric_types.append(metric_type)
        return metric_types

    @classmethod
    def update_device_metrics(cls, device, force_sync=False):
        if device.type == NON_PAYG_TYPE:
            return
        metric_types = cls.get_device_metric_types(device, force_sync=force_sync)
        for metric_type in metric_types:
            last_metric_pull_date = orm.max(metric.time for metric in Metric if metric.device == device and metric.metric_type.uuid == metric_type.uuid and metric.time <= datetime.now())
            if last_metric_pull_date is None:
                last_metric_pull_date = datetime.min
            metric_values = DeviceAPIService.get_usage_metrics_data_for_device(device, metric_type.uuid, last_metric_pull_date)
            if metric_values is None:
                continue
            for metric_value in metric_values:
                metric = Metric(
                    device=device,
                    metric_type=metric_type,
                    time=metric_value["time"],
                    value=metric_value.get("value"),
                    secondary_value=metric_value.get("secondary_value"),
                    text_value=metric_value.get('string', '')
                )

    @classmethod
    @db_session
    def update_all_device_metrics(cls):
        devices = DeviceListService.get_devices_in_use_that_support_usage_monitoring()
        print(f'Updating {devices.count()} devices')
        for device in devices:
            try:
                cls.update_device_metrics(device)
            except Exception as e:
                print(f'Error updating device metrics for {device.composed_serial}: {e}')
