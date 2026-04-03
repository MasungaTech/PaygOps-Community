import re
from shared.logger.loggers import Error
from pony import orm
from decimal import Decimal, DecimalException
from survey_system.models.question_type import PictureType, QuestionType
from survey_system.models.question import Question
from survey_system.models.answer import Answer
from survey_system.models.ordered_question import OrderedQuestion
from survey_system.models.question_text import QuestionText
from survey_system.models.question_choice import QuestionChoice
from survey_system.models.question_choice_text import QuestionChoiceText
from slugify import slugify
from constants import AVAILABLE_ICONS


class QuestionService:

    @classmethod
    def get_non_system_questions(cls):
        system_questions = cls.get_system_questions()
        questions = orm.select(question for question in Question if question not in system_questions)
        return questions

    @classmethod
    def get_system_questions(cls):
        system_questions = orm.select(question.question for question in OrderedQuestion if question.survey.form.is_system)
        questions = orm.select(question for question in Question if question in system_questions)
        return questions

    @classmethod
    def get_all_questions(cls):
        questions = orm.select(question for question in Question)
        return questions

    @classmethod
    def question_is_multi_type(cls,  question_type_id):
        return (question_type_id in [0, 2, 3, 4, 5])

    @classmethod
    def question_cannot_be_required(cls, question_type_id):
        return (question_type_id in [10])

    @classmethod
    def get_questions_by_name(cls, question_name):
        return orm.select(question for question in Question if question.name == question_name)


class AnswerStatsService:

    @classmethod
    def get_average_answer_from_questions_and_clients(cls, questions, clients):
        answers = orm.select(answer for answer in Answer
                             if answer.question in questions
                             and (answer.surveyAnswer.client_answering in clients
                             or (answer.surveyAnswer.lead_answering 
                                 and answer.surveyAnswer.lead_answering.person.client 
                                and answer.surveyAnswer.lead_answering.person.client in clients)))
        average = orm.avg(answer.value_numeric for answer in Answer if answer in answers)
        return average


class QuestionSorter:
    def sort_by(resultset, sort_param, sort_order):
        fields = {
            'id': Question.id,
            'name': Question.name,
            'version': Question.version,
            'type': Question.type
        }

        field = fields.get(sort_param, Question.id)

        if sort_order == 'desc':
            resultset = resultset.order_by(orm.desc(field))
        else:
            resultset = resultset.order_by(field)

        return resultset

class QuestionCreator:

    MAXUNITS = {
        QuestionType.numeric: 'value',
        QuestionType.text: 'length',
        QuestionType.long_text: 'length'
    }

    @classmethod
    def validate(cls, params):

        if not params.get('name'):
            raise Error('Name is required.')

        if params.get('type') is None:
            raise Error('Type is required.')

        if params.get('icon') and params.get('icon') not in AVAILABLE_ICONS:
            raise Error(f"The icon '{params.get('icon')}' does not exist")
        
        try:
            qtype = int(params.get('type'))
        except Exception:
            raise Error(f'Invalid Question Type "{params.get("type")}"')

        if not QuestionType.valid(qtype):
            raise Error(f'Invalid Question Type "{params.get("type")}"')

        if not params.get('full_question'):
            raise Error('Full Question Name is required.')
        
        if qtype in cls.MAXUNITS:
            max_unit = cls.MAXUNITS[qtype]
            if params.get('minValue'):
                try:
                    int(params.get('minValue'))
                except (TypeError, ValueError):
                    raise Error(f'Minimum {max_unit} must be a integer.')

            if params.get('maxValue'):
                try:
                    int(params.get('maxValue'))
                except (TypeError, ValueError):
                    raise Error(f'Maximum {max_unit} must be a integer.')
        
        if qtype in [QuestionType.choice_text, QuestionType.choice_numeric]:
            if not params.get('choices'):
                raise Error('Please set at least one option')
            for choice in params.get('choices'):
                try:
                    int(choice['order'])
                except (TypeError, ValueError):
                    raise Error('Order must be an integer not "'+choice['order']+'".')
                if not choice.get('value'):
                    raise Error('The option text cannot be empty')
                if qtype == QuestionType.choice_numeric:
                    try:
                        Decimal(choice['value'])
                    except (ValueError, TypeError, DecimalException):
                        raise Error('The options\' value must be numeric')
                    
        if qtype == QuestionType.picture: 
            additional_data = params.get('additional_data') or {}   
            if not additional_data.get('picture_type'):
                additional_data['picture_type'] = 'generic'
            if additional_data['picture_type'] not in ['generic', 'face_picture', 'id_credit_card_picture', 'passport_picture', 'a4_landscape_picture', 'a4_portrait_picture']:
                raise Error(f'Invalid picture type: {additional_data.get("picture_type")}')
            if 'picture_instructions' in additional_data and not isinstance(additional_data['picture_instructions'], str):
                raise Error('Picture instructions must be a string')
            
        if qtype == QuestionType.regex:
            additional_data = params.get('additional_data', {})
            if 'regex' not in additional_data or not additional_data['regex']:
                raise Error('Regex is required')

    @classmethod
    def create(cls, params, version=1):
        question_type = int(params.get('type'))
        name = params.get('name')
        icon = params.get('icon', '')
        language = params.get('language', 1)
        full_question = params.get('full_question', '')

        if params.get('minValue') == '':
            min_value = None
        else:
            min_value = params.get('minValue')

        if params.get('maxValue') == '':
            max_value = None
        else:
            max_value = params.get('maxValue')

        unit = params.get('unit', '')
        choices = params.get('choices', [])


        # Add picture_type and picture_instructions to additional_data
        additional_data = params.get('additional_data', {})
    
        question = cls.create_question(question_type=question_type,
                                       name=name,
                                       icon=icon,
                                       language=language,
                                       full_question=full_question,
                                       min_value=min_value,
                                       max_value=max_value,
                                       unit=unit,
                                       version=version,
                                       isInt=params.get('isInt', False),
                                       additional_data=additional_data)

        if question_type == QuestionType.choice_text:
            cls.create_choice_text_question(question, choices, language)

        if question_type == QuestionType.choice_numeric:
            cls.create_choice_numeric_question(question, choices)

        return question

    @classmethod
    @orm.db_session
    def create_question(cls, question_type, name, icon, language, full_question, min_value=None, max_value=None, unit='', version=1, isInt=False, additional_data=None):
        if additional_data and additional_data.get('regex'):
            if not cls.is_valid_regex(additional_data.get('regex')):
                raise Error("Invalid RegEx")
        question = Question(name=name,
                            slug=slugify(name),
                            type=question_type,
                            icon=icon,
                            minValue=min_value,
                            maxValue=max_value,
                            unit=unit,
                            version=version,
                            isInt=isInt,
                            additional_data=additional_data if additional_data else {})

        QuestionText(language=language,
                     question=question,
                     fullQuestion=full_question,
                     variableName=name)

        orm.commit()

        return question

    @classmethod
    def create_choice_text_question(cls, question, choices, language):
        for choice in choices:
            question_choice = QuestionChoice(question=question, order=choice.get('order'))
            QuestionChoiceText(questionChoice=question_choice,
                               language=language,
                               value_text=choice.get('value'))

    @classmethod
    def create_choice_numeric_question(cls, question, choices):
        for choice in choices:
            QuestionChoice(question=question,
                           order=choice.get('order'),
                           value_numeric=choice.get('value', 0))

    @classmethod
    def create_question_from_api_data(cls, api_data):
        FIELD_MAPPING = {
            'min_value': 'minValue',
            'max_value': 'maxValue',
            'text': 'full_question',
        }
        old_format_dict = {FIELD_MAPPING.get(k, k): v for k, v in api_data.items()}
        if old_format_dict['type'] == 'integer':
            old_format_dict['type'] = QuestionType.numeric
            old_format_dict['isInt'] = True
        else:
            old_format_dict['type'] = QuestionType.to_dict().get(old_format_dict['type'])
        if old_format_dict.get('choices'):
            new_choices = []
            order = 0
            for choice in old_format_dict.get('choices'):
                order += 1
                new_choices.append({
                    'order': order,
                    'value': choice
                })
            old_format_dict['choices'] = new_choices
        cls.validate(old_format_dict)
        return cls.create(old_format_dict)

    def is_valid_regex(regex):
        try:
            re.compile(regex)
            return True
        except re.error as e:
            return False
