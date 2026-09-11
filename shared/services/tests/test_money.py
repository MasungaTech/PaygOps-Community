from pony.orm import db_session
from shared.services.money import MoneyFormatter
from shared.services.settings_service import SettingsService


class TestMoney:

    @db_session
    def test_format_amount(self):
        expected = '13,667,995 {}'.format(SettingsService.get_setting('CurrencySymbol'))
        assert expected == MoneyFormatter.format(13667995)

    @db_session
    def test_format_with_amount_none(self):
        assert '0 {}'.format(SettingsService.get_setting('CurrencySymbol')) == MoneyFormatter.format(None)

    @db_session
    def test_format_with_currency(self):
        expected = '13,667,995'.format(SettingsService.get_setting('CurrencySymbol'))
        assert expected == MoneyFormatter.format(13667995, with_currency=False)
