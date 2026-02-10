import json
from config import ENV_VAR, TRANSLATION_FOLDER, IS_TEST_PLATFORM, IS_TESTING, BUILD_MODE
import os
import markupsafe
from flask_login import current_user
from flask import has_request_context, request

global TRANSLATION_CACHE
TRANSLATION_CACHE = {}


class NoTranslate(str):

    NOTRANSLATE = True

    def __init__(self, text):
        self = text


class TranslationService:

    @classmethod
    def ftext(cls, text, *args, force=False, user=None, current=False, **kwargs):
        if not user and current:
            user=current_user
        text = TranslationService.get_translated_string(text, getattr(user, 'person', None), force=force)
        if not len(args) and not len(kwargs):
            return text
        return text.format(*args, **kwargs)
    
    @classmethod
    def get_language_for_user(cls, user=None):
        person = getattr(user, 'person', None)
        if not person:
            return 'EN'
        return cls.get_language_from_person(person)

    @classmethod
    def is_notranslate(cls, variable, force=False):
        if isinstance(variable, NoTranslate):
            return True
        if not force and isinstance(variable, markupsafe.Markup):
            return True
        return False
    
    @classmethod
    def make_notranslate(cls, variable):
        return NoTranslate(variable)
    
    @classmethod
    def _generate_mock_key(cls, key):
        mock_key = ''
        replace = True
        for x in key:
            if x in ['{']:
                mock_key += x
                replace = False
            elif x in ['}']:
                mock_key += x
                replace = True
            elif replace and x not in [' ', '(', ')']: 
                mock_key += 'x'
            else:
                mock_key += x
        return mock_key
    
    @classmethod
    def get_language_from_person(cls, person):
        language = getattr(person, 'get_language', None)
        return language() if language else 'EN'

    @classmethod
    def get_translated_string(cls, key, person=None, force=False):
        if cls.is_notranslate(key, force):
            return key
        # We only check while in development or on test platforms
        if IS_TEST_PLATFORM:
            cls.check_missing_keys(key)
        if has_request_context():
            lkey = 'person_language_'+str(getattr(person, 'id', 'noid'))
            pl = request.environ.get(lkey)
            if pl:
                language = pl
            else:
                language = cls.get_language_from_person(person)
                request.environ[lkey] = language
        else:
            language = cls.get_language_from_person(person) 
        if language == 'EN':
            return NoTranslate(key)    
        if language == 'XX':
            return NoTranslate(cls._generate_mock_key(key))
        language_dict = cls.load_language_file(language)
        return NoTranslate(language_dict.get(key, key))

    @classmethod
    def load_language_file(cls, language):
        cached = TRANSLATION_CACHE.get(language)
        if cached:
            return cached
        try:
            language_file = open(TRANSLATION_FOLDER+f'/{language}/{language}.json', "r")
            lang_data = language_file.read()
            language_file.close()
            translation_data = json.loads(lang_data or "{}")
            TRANSLATION_CACHE[language] = translation_data
            return translation_data
        except FileNotFoundError:
            return {}

    @classmethod
    def check_missing_keys(cls, key):
        new_key = False
        if TRANSLATION_CACHE.get('keys'):
            keys = TRANSLATION_CACHE.get('keys')
        else:
            try:
                key_file = open(TRANSLATION_FOLDER+'keys.json', "r")
            except Exception as e:
                key_file = open(TRANSLATION_FOLDER+'keys.json', "w+")
            try:
                key_file_data = key_file.read()
                keys = json.loads(key_file_data or "[]")
                TRANSLATION_CACHE['keys'] = keys
            except Exception as e:
                print('Impossible to check missing key: '+str(e))
        if key not in keys:
            print('new key found', key)
            new_key = True
            # We only store if not in automated tests
            if not IS_TESTING:
                keys.append(key)
                key_file = open(TRANSLATION_FOLDER+'keys.json', "w+")
                key_file.write(json.dumps(keys, ensure_ascii=False, indent=2))
        if new_key:
            try:
                if TRANSLATION_CACHE.get('new_keys'):
                    new_keys = TRANSLATION_CACHE.get('new_keys')
                else:
                    try:
                        new_key_file = open(TRANSLATION_FOLDER+'new_keys.json', "r")
                    except Exception as e:
                        new_key_file = open(TRANSLATION_FOLDER+'new_keys.json', "w+")
                    new_keys = json.loads(new_key_file.read() or "[]")
                new_keys.append(key)
                TRANSLATION_CACHE['new_keys'] = new_keys
                open(TRANSLATION_FOLDER+'new_keys.json', "w+").write(json.dumps(new_keys, ensure_ascii=False, indent=2))
            except Exception as e:
                print('Impossible to add new missing key: '+str(e))

    @classmethod
    def get_js_language_file_content(cls, language):
        if ENV_VAR == 'TEST' and BUILD_MODE == '0': return 'var PaygOps_LNG = {}'
        language = language.upper()
        lng_file = open(TRANSLATION_FOLDER+f'{language}/{language}_js_msg.json', "r")
        lng_file_data = lng_file.read()
        return 'var PaygOps_LNG = '+lng_file_data
