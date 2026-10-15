from shared.services.settings_service import SettingsService


class MoneyFormatter:
    @staticmethod
    def format(amount, with_currency=True):
        if amount is None:
            amount = 0

        if with_currency:
            return '{:,} {}'.format(round(amount, 2), SettingsService.get_setting('CurrencySymbol'))

        return '{:,}'.format(round(amount, 2))
