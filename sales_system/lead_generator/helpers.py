from datetime import datetime, timedelta


def set_date(request, key):
    finish_date = request.form.get(key)
    return datetime.strptime(finish_date, '%Y-%m-%d')

def set_date_from_str(str_date):
    return datetime.strptime(str_date, '%Y-%m-%d')

def valid_dates(begin_date, end_date, nxt_mnth):
    if begin_date >= end_date or end_date > nxt_mnth:
        return None
    return True


def next_month(today):
    if today.month + 2 <= 12:
        return datetime(today.year, today.month + 2, 1) - timedelta(days=1)
    else:
        return datetime(today.year + 1, (today.month + 2) - 12, 1) - timedelta(days=1)


def get_current_day_month_year():
    current_date = datetime.now()
    return current_date.day, current_date.month, current_date.year


def get_previous_month(month, year):
    month -= 1
    if month < 1:
        month = 12
        year -= 1
    return month, year


