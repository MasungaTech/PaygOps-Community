from constants import LATITUDE_PATTERN, LONGITUDE_PATTERN
from shared.api_helpers.server_helpers.jwt_and_schema_verification import validate_schema
from survey_system.methods.helper import is_valid_url
from survey_system.models.question_type import QuestionType
from shared.logger.loggers import Error
from pony import orm
import dateutil
from shared.file_upload.services.stored_file_service import StoredFileService
from core_system.core_entities import db
from core_system.operational_entities.models import OperationalEntity
import pytz
from munch import DefaultMunch
from survey_system.models.languages import Languages
import re

class AnswerService:

    @classmethod
    def normalize_value(cls, question, value, use_names):
        # This is a trick to be able to get the equivalent getValue() from just the raw received value
        answer = DefaultMunch(None, {})
        answer.question = question.question
        def getValue():
            return AnswerService.get_answer_value(answer, Languages.english)
        answer.getValue = getValue
        cls.set_answer_value(answer, value, use_names)
        return answer.getValue()
    
    @classmethod
    def set_answer_value(cls, answer, value, use_names):
        if not cls._is_value_valid(value):
            raise Error('EMPTY_ANSWER', {'question_name': answer.question.name})
        if answer.question.type == QuestionType.yes_no:
            cls._set_bool_answer(answer, value)
        elif answer.question.type == QuestionType.checkbox:
            cls._set_checkbox_answer(answer, value)
        elif answer.question.type == QuestionType.text or answer.question.type == QuestionType.long_text:
            cls._set_text_answer(answer, value)
        elif answer.question.type == QuestionType.numeric:
            cls._set_numeric_question(answer, value)
        elif answer.question.type == QuestionType.choice_text:
            cls._set_choice_text_question(answer, value, use_names)
        elif answer.question.type == QuestionType.choice_numeric:
            cls._set_choice_numeric_question(answer, value, use_names)
        elif answer.question.type == QuestionType.picture:
            cls._set_picture_question(answer, value)
        elif answer.question.type == QuestionType.date:
            cls._set_datetime_question(answer, value)
        elif answer.question.type == QuestionType.gps:
            cls._set_gps_question(answer, value)
        elif answer.question.type == QuestionType.gps_surface:
            cls._set_gps_surface(answer, value)
        elif answer.question.type == QuestionType.url:
            cls._set_url_answer(answer, value)
        elif answer.question.type == QuestionType.signature:
            cls._set_signature_question(answer, value)
        elif answer.question.type == QuestionType.regex:
            cls._set_regex_question(answer, value)
        elif answer.question.type == QuestionType.l0_entity:
            cls._set_l0_entity_question(answer, value)
        else:
            raise Error('INVALID_QUESTION_TYPE', {'question_name': answer.question.name, 'question_type': answer.question.type})

    @classmethod
    def _set_bool_answer(cls, answer, value):
        if value in ['1', 'yes', 'Yes', 'true', 'True', True]:
            answer.value_bool = True
            answer.value_text = 'Yes'
        else:
            answer.value_bool = False
            answer.value_text = 'No'

    @classmethod
    def _set_checkbox_answer(cls, answer, value):
        if value in [True, 'true', 'True', 1, '1']:
            answer.value_bool = True
            answer.value_text = 'Yes'
        else:
            answer.value_bool = False
            answer.value_text = 'No'

    @classmethod
    def _set_text_answer(cls, answer, value):
        value = str(value)
        if answer.question.minValue is not None and len(value) < answer.question.minValue:
            raise Error('ANSWER_TOO_SHORT', {'question_name': answer.question.name, 'min_value': answer.question.minValue})
        if answer.question.maxValue is not None and len(value) > answer.question.maxValue:
            raise Error('ANSWER_TOO_LONG', {'question_name': answer.question.name, 'max_value': answer.question.maxValue})
        answer.value_text = value

    @classmethod
    def _set_url_answer(cls, answer, value):
        if not is_valid_url(value):
            raise Error('INVALID_URL', {'question_name': answer.question.name})
        cls._set_text_answer(answer, value)

    @classmethod
    def _set_numeric_question(cls, answer, value):
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            raise Error(f'Value "{str(value)}" cannot be converted into decimal, check for any non-numerical characters')
        if answer.question.minValue is not None and numeric_value < answer.question.minValue:
            raise Error('VALUE_TOO_LOW', {'question_name': answer.question.name, 'min_value': answer.question.minValue})
        if answer.question.maxValue is not None and numeric_value > answer.question.maxValue:
            raise Error('VALUE_TOO_HIGH', {'question_name': answer.question.name, 'max_value': answer.question.maxValue})
        if answer.question.isInt and not numeric_value.is_integer():
            raise Error('VALUE_NOT_INTEGER', {'question_name': answer.question.name})
        answer.value_numeric = numeric_value

    @classmethod
    def _set_choice_text_question(cls, answer, value, use_names):
        choice = None
        if use_names:
            choice_text = orm.select(C for C in db.QuestionChoiceText if C.value_text == value
                                     and C.questionChoice.question == answer.question).first()
            if choice_text:
                choice = choice_text.questionChoice
        else:
            choice = orm.select(C for C in db.QuestionChoice if C.id == int(value)).first()
        if choice and choice.question == answer.question:
            answer.value_choice = choice
        else:
            raise Error('INVALID_QUESTION_CHOICE', {'question_name': answer.question.name})
        answer.value_text = answer.getValue()

    @classmethod
    def _set_choice_numeric_question(cls, answer, value, use_names):
        if use_names:
            choice = orm.select(C for C in db.QuestionChoice if C.value_numeric == float(value)
                                and C.question == answer.question).first()
        else:
            choice = orm.select(C for C in db.QuestionChoice if C.id == int(value)).first()
        if choice is not None:
            if choice.question == answer.question:
                answer.value_choice = choice
            else:
                raise Error('INVALID_QUESTION_CHOICE', {'question_name': answer.question.name})
        else:
            raise Error('INVALID_QUESTION_CHOICE', {'question_name': answer.question.name})
        answer.value_numeric = answer.getValue()

    @classmethod
    def _set_picture_question(cls, answer, value):
        this_picture = StoredFileService.get_from_uuid(value)
        if this_picture is not None:
            answer.value_stored_file = this_picture
        else:
            raise Error('INVALID_PICTURE_ID', {'question_name': answer.question.name})

    @classmethod
    def _set_signature_question(cls, answer, value):
        this_signature = StoredFileService.get_from_uuid(value)
        if this_signature is not None:
            answer.value_stored_file = this_signature
        else:
            raise Error('INVALID_SIGNATURE_ID', {'question_name': answer.question.name})

    @classmethod
    def _set_datetime_question(cls, answer, value):
        try:
            value_date = dateutil.parser.parse(value) if value else None
            if value_date:
                value_date = value_date.astimezone(pytz.utc).replace(tzinfo=None)
            answer.value_date = value_date
        except (ValueError, TypeError):
            raise Error('Invalid format for date "'+value+'".')

    @classmethod
    def _set_gps_question(cls, answer, value):
        try:
            lat = value.get('lat', value.get('gps_latitude'))
            lon = value.get('lon', value.get('gps_longitude'))
            answer.value_text = str(lat)+';'+str(lon)
        except (ValueError, TypeError):
            raise Error('Invalid format for gps "'+str(value)+'".')

    @classmethod
    def _set_gps_surface(cls, answer, value):
        empty_value = [{'gps_latitude': '', 'gps_longitude': ''}, {'gps_latitude': '', 'gps_longitude': ''}, {'gps_latitude': '', 'gps_longitude': ''}]
        if value == empty_value:
            value = []
        if value:
            validate_schema(value, {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "gps_latitude": {
                            "oneOf": [
                                {
                                    "type": "number",
                                    "minimum": -90,
                                    "maximum": 90
                                },
                                {
                                    "type": "string",
                                    "pattern": LATITUDE_PATTERN
                                }
                            ]
                        },
                        "gps_longitude": {
                            "oneOf": [
                                {
                                    "type": "number",
                                    "minimum": -180,
                                    "maximum": 360
                                },
                                {
                                    "type": "string",
                                    "pattern": LONGITUDE_PATTERN
                                }
                            ]
                        }
                    },
                    "additionalProperties": False
                },
                "minItems": 3,
                "maxItems": 50
            })
        answer.value_json = value

    @classmethod
    def _set_regex_question(cls, answer, value):
        value = str(value)
        regex_pattern = r"%s" % answer.question.additional_data.get("regex")
        if not re.fullmatch(regex_pattern, value):
            raise Error('Invalid %s Format' % answer.question.name)
        answer.value_text = value

    @classmethod
    def _set_l0_entity_question(cls, answer, value):
        if value:
            entity = orm.select(E for E in OperationalEntity if E.id == int(value)).first()
            if entity:
                answer.value_numeric = int(value)
            print('VALUE', value, 'ENTITY', entity)
        if not entity:
            raise Error('Invalid L0 Entity ID: '+str(value))

    @classmethod
    def _is_value_valid(cls, value):
        if value is None or value == '':
            return False
        return True

    @classmethod
    def get_value(cls, answer, language=None, use_names=False, mobile=False):
        question = answer.question
        if question.type == QuestionType.choice_text and not use_names:
            answer = answer.value_choice.id if answer.value_choice else None
        elif question.type == QuestionType.choice_numeric and not use_names:
            answer = answer.value_choice.id if answer.value_choice else None
        elif answer.question.type in [QuestionType.picture, QuestionType.signature]:
            answer = answer.getValue(language=language)
            if answer:
                answer = answer.uuid
        elif question.type == QuestionType.gps:
            lat, lon = answer.value_text.split(';')
            if mobile:
                answer = {
                    "lat": lat,
                    "lon": lon
                }
            else:
                answer = {
                    "gps_longitude": lon,
                    "gps_latitude": lat
                }
        elif question.type == QuestionType.gps_surface:
            answer = answer.value_json
        else:
            answer = answer.getValue(language=language)
        return answer
    
    @classmethod
    def get_answer_value(cls, answer, language):
        if answer.question.type == QuestionType.yes_no or answer.question.type == QuestionType.checkbox:
            return answer.value_bool
        elif answer.question.type == QuestionType.text or answer.question.type == QuestionType.long_text or answer.question.type == QuestionType.url:
            return answer.value_text
        elif answer.question.type == QuestionType.numeric:
            if answer.question.isInt and answer.value_numeric is not None:
                return int(answer.value_numeric)
            else:
                return answer.value_numeric
        elif answer.question.type == QuestionType.choice_text:
            return answer.value_choice.getText(language) if answer.value_choice is not None else None
        elif answer.question.type == QuestionType.choice_numeric:
            if answer.value_choice is None:
                return None
            if answer.question.isInt:
                return int(answer.value_choice.getValue())
            else:
                return answer.value_choice.getValue()
        elif answer.question.type == QuestionType.group:
            return None
        elif answer.question.type == QuestionType.picture:
            return answer.value_stored_file
        elif answer.question.type == QuestionType.signature:
            return answer.value_stored_file
        elif answer.question.type == QuestionType.date:
            return answer.value_date
        elif answer.question.type == QuestionType.gps:
            return 'Latitude: {}º / Longitude: {}º'.format(*answer.value_text.split(';'))
        elif answer.question.type == QuestionType.gps_surface:
            return answer.value_json
        elif answer.question.type == QuestionType.regex:
            return answer.value_text
        elif answer.question.type == QuestionType.l0_entity:
            return answer.value_numeric
        else:
            raise Error('INVALID_QUESTION_TYPE', {'question_name': answer.question.name})
