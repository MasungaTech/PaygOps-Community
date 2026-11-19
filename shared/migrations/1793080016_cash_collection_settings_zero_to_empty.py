from decimal import Decimal, InvalidOperation

from pony.orm import db_session

# 0 used to mean "unlimited" / "deactivated" for these settings, now an empty value does
NULLABLE_CASH_COLLECTION_SETTINGS = ['CashCollectionLimit', 'CashCollectionPercentageWarning', 'CashCollectionAmountWarning']


def _is_zero(value):
    try:
        return Decimal(value) == 0
    except (InvalidOperation, TypeError):
        return False


@db_session
def up(db):
    for key in NULLABLE_CASH_COLLECTION_SETTINGS:
        setting = db.Settings.get(key=key)
        if setting and _is_zero(setting.value):
            setting.value = ''


@db_session
def down(db):
    for key in NULLABLE_CASH_COLLECTION_SETTINGS:
        setting = db.Settings.get(key=key)
        if setting and setting.value == '':
            setting.value = '0'
