from datetime import datetime, timedelta


def timePeriodHelper(time_period, default=14):
    time_period = time_period if time_period in ['3', '7', '14', '30', '90', 'forever'] else default

    return datetime.min if time_period == 'forever' else datetime.now() - timedelta(days=int(time_period))
