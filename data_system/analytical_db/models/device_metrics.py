from datetime import datetime
from pony.orm import select, Set
from shared.helpers.db_helpers import Optional, PrimaryKey
from payg_loan_system.devices.model.device_metrics_model import Metric, MetricFormat
from data_system.analytical_db.analytical_db import analytical_db
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
import config

class Device_Metrics(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'Individual data points of metrics coming from devices. This is only available for connected devices and varies from device to device (e.g. some devices will report the battery voltage and current, while other might report the number of liters of water pumped)'

    base_model = Metric

    id = PrimaryKey(int, comment="The internal unique ID of the device metric")
    device_serial_number = Optional(str, index=True, comment="The composed serial number of the device (including manufacturer prefix)")
    stock_item_id  = Optional('Stock_Items', comment="The stock item that the device metric is associated with (if any)")
    date = Optional(datetime, index=True, comment="The date at which this particular data point of the metric was recorded")
    name = Optional(str, index=True, comment="The name of the particular metric")
    unit = Optional(str, comment="The unit of the metric")
    format = Optional(str, comment="The format of the metric (Numeric, String, GPS or Alert)")
    
    value_numeric = Optional(float, index=True, comment="The numeric value of the metric (if applicable)")
    value_text = Optional(str, comment="The text value of the metric (if applicable)")
    value_gps_longitude = Optional(float, comment="The WGS84 longitude value recorded for the metric (if GPS metric)", precision=4)
    value_gps_latitude = Optional(float, comment="The WGS84 latitude value recorded for the metric (if GPS metric)", precision=4)
    # Internal
    last_updated = Optional(datetime, comment=config.LAST_UPDATED_DEFINITION)

    @staticmethod
    def converter(metric):
        return {
            'id': metric[0],
            'device_serial_number': metric[1].composed_serial,
            'stock_item_id': metric[1].stock_item.id,
            'name': metric[2].name or '',
            'unit': metric[2].credit_unit or '',
            'format': metric[2].format or '',
            'date': metric[3],
            'value_numeric': metric[4] if metric[2].format == MetricFormat.numeric else None,
            'value_text': metric[6] if metric[2].format == MetricFormat.string else '',
            'value_gps_longitude': metric[4] if metric[2].format == MetricFormat.gps else None,
            'value_gps_latitude': metric[5] if metric[2].format == MetricFormat.gps else None,
            'last_updated': metric[7]
        }

    @staticmethod
    def selector(objects):
        return select((
            s.id,
            s.device,
            s.metric_type,
            s.time,
            s.value,
            s.secondary_value,
            s.text_value,
            Device_Metrics.extended_modified_date(s)
        ) for s in objects).order_by(8)
