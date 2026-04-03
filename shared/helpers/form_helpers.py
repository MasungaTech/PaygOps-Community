from datetime import datetime
from shared.logger.loggers import Error
from datetime import timezone
from shared.helpers.clock import Clock

import dateutil


def dateTimePickerToStandard(dateString, timeString=''):
    thisDatetime = None
    fmt = '%Y-%m-%d'

    if dateString != '':
        try:
            thisDatetime = datetime.strptime(dateString, fmt).date()
        except ValueError as v:
            ulr = len(v.args[0].partition('unconverted data remains: ')[2])
            if ulr:
                thisDatetime = datetime.strptime(dateString[:-ulr], fmt)
            else:
                raise v

    if thisDatetime and timeString != '':
        thisTime = datetime.strptime(timeString, '%H:%M').time()
        thisDatetime = datetime.combine(thisDatetime, thisTime)
    
    return thisDatetime

def naiveDateTimeToStandard(dateString):
    if not dateString or dateString == '':
        return None
    return datetime.fromisoformat(dateString)

def isoDateTimeToStandard(dateString):
    thisDatetime = None
    if dateString != '':
        try:
            thisDatetime = datetime.fromisoformat(dateString[:-1]).astimezone(timezone.utc)
        except ValueError as v:
            thisDatetime = datetime.fromisoformat(dateString)
    return thisDatetime


def isoDateTimeToUTC(dateString, naive=True):
    return isoDateTimeToStandard(dateString).replace(tzinfo=None) if naive else isoDateTimeToStandard(dateString)

def formBoolConverter(bool_variable, data):
    if bool_variable in data:
        return True
    else:
        return False


def datetime_string_to_datetime(date_string):
    this_datetime = None
    try:
        this_datetime = datetime.strptime(date_string, '%Y-%m-%d')
    except:
        try:
            this_datetime = dateutil.parser.parse(date_string)
        except:
            pass
    if not this_datetime:
        raise Error('INVALID_DATETIME_FORMAT')
    return this_datetime


def value_to_bool(this_value):
    if isinstance(this_value, str):
        this_value = this_value.lower()
    if this_value in ['yes', 'true', True, '1', 1]:
        return True
    return False

def value_if_not_empty(this_value):
    if this_value in ['', None]:
        return None
    else:
        return this_value