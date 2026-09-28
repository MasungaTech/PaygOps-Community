from shared.services.settings_service import SettingsService
import config


class LanguageService:

    @classmethod
    def get_client_sms_language_dict(cls):
        client_languages = config.AVAILABLE_CLIENTS_SMS_LANGUAGES
        language_names = config.LANGUAGES_NAMES
        if SettingsService.get_setting('CustomLanguageName'):
            language_names.update({'CU': SettingsService.get_setting('CustomLanguageName')})
        client_language_dict = {k: language_names[k] for k in client_languages if k in language_names}
        return client_language_dict

    @classmethod
    def get_user_sms_language_dict(cls):
        return config.AVAILABLE_USERS_LANGUAGES
