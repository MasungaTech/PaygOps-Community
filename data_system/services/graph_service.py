from datetime import datetime, timedelta
from shared.helpers.clock import Clock
from shared.helpers.form_helpers import dateTimePickerToStandard

class GraphService:

    @classmethod
    def process_input_time(cls, input_time, from_time, localize=True):
        if not input_time:
            if from_time:
                return datetime.now() - timedelta(days=365)
            else:
                return datetime.now()
        else:
            if from_time:
                input_time_obj = dateTimePickerToStandard(input_time)
                if localize:
                    return Clock.localize_to_utc(input_time_obj)
                else:
                    return input_time_obj
            else:
                input_time_obj = dateTimePickerToStandard(input_time) #+ timedelta(days=1)
                if localize:
                    return Clock.localize_to_utc(input_time_obj)
                else:
                    return input_time_obj

    @classmethod
    def generate_monthly_graph_data(cls, from_time, to_time, value_function, value_function_2=None, value_function_3=None, **kwargs):
        data = []
        number_of_months = cls._get_number_of_months_between_time(from_time, to_time)
        # Always add 1 to include both the start and end months
        number_of_months += 1
        first_month = cls._get_month_number_from_time(from_time)
        for month in range(number_of_months):
            prev_month_time = cls._get_month_time(-first_month-month)
            month_time = cls._get_month_time(-first_month-month-1)
            label = cls._get_label_from_month_time(prev_month_time)
            value = value_function(from_time=prev_month_time, to_time=month_time, **kwargs)
            if value_function_2:
                value_2 = value_function_2(from_time=prev_month_time, to_time=month_time, **kwargs)
                if value_function_3:
                    value_3 = value_function_3(from_time=prev_month_time, to_time=month_time, **kwargs)
                    data.append((label, value, value_2, value_3))
                else:
                    data.append((label, value, value_2))
            else:
                data.append((label, value))
        return data

    @classmethod
    def _get_number_of_months_between_time(cls, from_time, to_time):
        return -((from_time.year - to_time.year) * 12 + (from_time.month - to_time.month))

    @classmethod
    def _get_month_number_from_time(cls, selected_time):
        return cls._get_number_of_months_between_time(cls._get_month_time(0), selected_time)

    @classmethod
    def _get_month_time(cls, month_number):
        months_before = month_number + 1
        today = datetime.today()
        y = today.year + ((today.month) - months_before - 1) // 12
        m = (today.month - months_before) % 12
        if not m:
            m = 12
        d = 1
        return datetime(y, m, d)

    @classmethod
    def _get_label_from_month_time(cls, selected_time):
        return selected_time.strftime("%b %Y")
