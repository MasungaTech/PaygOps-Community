from datetime import datetime, date, timezone
import dateutil
import decimal


def json_serializer(obj):
    if isinstance(obj, (datetime, date)):
        serial = obj.isoformat()
        return serial
    if isinstance(obj, decimal.Decimal):
        # wanted a simple yield str(o) in the next line,
        # but that would mean a yield on the line with super(...),
        # which wouldn't work (see my comment below), so...
        return float(str(obj))
    raise TypeError("Type %s not serializable" % type(obj))


def add_utc_tz_info(dt):
    dt = dt.replace(tzinfo=timezone.utc)
    return dt


def datetime_from_string(dateStr, isAddUtcTzInfo=False):
    if type(dateStr) != int:
        if dateStr.count('-') < 2:
            return dateStr
    # use dateutil parser here because it can parse ISO 8601 format
    dt = dateutil.parser.parse(dateStr, ignoretz=not isAddUtcTzInfo)
    if isAddUtcTzInfo:
        dt = add_utc_tz_info(dt)

    return dt

def try_parse(date):
    try:
        return datetime_from_string(date)
    except:
        return date

def json_date_hook(json_dict):
    if isinstance(json_dict, dict):
        return {key: try_parse(value) for key, value in json_dict.items()}
    if isinstance(json_dict, list):
        return [try_parse(value) for value in json_dict]
    return json_dict
