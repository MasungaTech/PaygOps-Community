from datetime import datetime
import calendar
from dateutil.relativedelta import relativedelta
import json
from shared.services.settings_service import SettingsService

from pony.orm import Required, Json, Optional, db_session, commit, desc

from shared.helpers.numbers import format_thousands
from core_system.core_entities import db
from shared.model.interface import ModelInterface


class HistoricalMethodBase(ModelInterface):
    @classmethod
    @db_session
    def all(cls, deleted=False):
        if deleted:
            return cls.select()

        return cls.select(lambda data: data.deleted_on is None)

    @db_session
    def soft_delete(self):
        self.deleted_on = datetime.now()
        commit()

    def content_dict(self):
        parsed_val = json.loads(self.content)
        date = self.calculated_on.strftime('%Y-%m-%d')

        return dict(calculated_on=date, content=parsed_val.get('value'))

    @staticmethod
    @db_session
    def most_recent(data_type):
        data = HistoricalData.select(lambda h: h.type == data_type)\
            .order_by(desc(HistoricalData.calculated_on)).first()

        if data is None:
            data = {}

        return data


class HistoricalData(db.Entity, HistoricalMethodBase):
    _table_ = "historical_data"
    type = Required(str)
    content = Required(Json)
    organization_id = Required(str)

    calculated_on = Required(datetime)
    deleted_on = Optional(datetime)
    modified_on = Optional(datetime)

    @staticmethod
    def sort(resultset, string, field_name="id", order="desc"):
        try:
            field_name, order = string.split(":")
        except ValueError as excep:
            print("Error {}".format(excep))
        finally:
            return HistoricalData._set_order(
                resultset, field_name.lower(), order)

    @staticmethod
    def _set_order(resultset, field_name, order):
        if field_name == 'calculated_on':
            if order.lower() == "desc":
                return resultset.order_by(lambda p: desc(p.calculated_on))
            return resultset.order_by(lambda p: p.calculated_on)
        else:
            if order.lower() == "desc":
                return resultset.order_by(desc(HistoricalData.id))
            return resultset.order_by(HistoricalData.id)


class RevenueAverage:
    TYPE = 'revenue_average'

    @staticmethod
    def recent_average_list():
        data = RevenueAverage.historical_data()
        if data:
            content = json.loads(data.content).get('value', {})
            return json.loads(content).get('average_list', [])

        return []

    @staticmethod
    def recent_amount():
        average_list = RevenueAverage.recent_average_list()
        data = RevenueAverage.historical_data()
        if data:
            content = json.loads(data.content).get('value', {})
            amount = json.loads(content).get('recent_average', 0)
            return format_thousands(amount)

        return 0

    @staticmethod
    def historical_data():
        return HistoricalData.most_recent(RevenueAverage.TYPE)

    @staticmethod
    def recent_data_response():
        data = RevenueAverage.historical_data()

        if not data:
            return {}

        return {
            'calculated_on': data.calculated_on.strftime('%Y-%m-%d'),
            'amount': '{} {}'.format(RevenueAverage.recent_amount(), SettingsService.get_setting('CurrencySymbol'))
        }

    @staticmethod
    def generate_data(stats):
        average_list = []

        end_date = datetime.today()
        start_date = end_date - relativedelta(months=1)

        start_date = start_date.replace(
            hour=0, minute=0, second=0, microsecond=0)

        recent_average = stats.recent_revenue_average(start_date, end_date)

        for i in range(1, 12):
            last_month = datetime.today() - relativedelta(months=i)
            _, last_day = calendar.monthrange(last_month.year, last_month.month)

            start_date = datetime(last_month.year, last_month.month, 1)
            end_date = datetime(last_month.year, last_month.month, last_day)

            key = start_date.strftime('%b %Y')
            average = stats.recent_revenue_average(start_date, end_date)
            average_list.append(
                {'month': key, 'amount': average, 'position': i})

        average_list = sorted(average_list, key=lambda a: a['position'])[::-1]

        return {
            'recent_average': recent_average,
            'average_list': average_list
        }
