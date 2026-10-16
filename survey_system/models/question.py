from datetime import datetime
from shared.logger.loggers import Error
from pony import orm
from slugify import slugify

from core_system.core_entities import db
from survey_system.models.question_type import PictureType, QuestionType
from survey_system.models.question_text import QuestionText
from survey_system.models.question_choice import QuestionChoice
from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from constants import AVAILABLE_ICONS


class Question(db.Entity, ModelDefinitionMixin):

    name = orm.Required(str)
    slug = orm.Optional(str, column='referencename') # New, used for the question getting
    type = orm.Required(int)
    updateDate = orm.Required(datetime, default=datetime.now)
    version = orm.Required(int, default=1)
    usable = orm.Required(bool, default=True)  # prevent just the creation of new surveys, can still be used in old ones

    icon = orm.Optional(str, py_check=lambda i: not i or i in AVAILABLE_ICONS)
    unit = orm.Optional(str)
    isInt = orm.Optional(bool, default=False)
    minValue = orm.Optional(int)
    maxValue = orm.Optional(int)
    updatedBy = orm.Optional('User', column="updatedby")

    text = orm.Set('QuestionText', cascade_delete=True)
    choices = orm.Set('QuestionChoice', cascade_delete=True)
    orderInSurvey = orm.Set('OrderedQuestion')
    answers = orm.Set('Answer', cascade_delete=True)
    additional_data = orm.Optional(orm.Json)

    def before_insert(self):
        self.slug = slugify(self.name)

    def before_update(self):
        self.slug = slugify(self.name)

    def after_insert(self):
        self.update_related_survey_cache()

    def after_update(self):
        self.update_related_survey_cache()

    def update_related_survey_cache(self):
        #Trigger update_cache for surveys so that they are updated on mobile
        for orderedQuestion in self.orderInSurvey:
            if orderedQuestion.survey:
                orderedQuestion.survey.update_cached_data()

    @property
    def full_question(self):
        return self.getText(1)
    
    def get_form(self):
        return orm.select(oq.survey.form for oq in self.orderInSurvey).first()

    def after_update(self):
        self._check_data_coherence()

    def before_insert(self):
        self._check_data_coherence()

        # We check that at least one QuestionText is defined before allowing usable to be True
        if (orm.count(self.text) == 0) and self.usable:
            raise ValueError

    def getText(self, language):
        return orm.select(T.fullQuestion for T in QuestionText if T.question == self and
                          T.language == language).first()

    def setText(self, text, language):
        self.text.filter(lambda t: t.language == language).first().fullQuestion = text

    def getVariableName(self, language):
        return orm.select(T.variableName for T in QuestionText if T.question == self and
                          T.language == language).first()

    def setVariableName(self, name, language):
        self.text.filter(lambda t: t.language == language).first().variableName = name

    def getChoices(self):
        return orm.select(C for C in QuestionChoice if C.question == self).order_by(QuestionChoice.order)

    def get_choices_list(self, language=None):
        if self.type == QuestionType.choice_numeric:
            return [(C.id, C.getValue()) for C in self.getChoices()]
        elif self.type == QuestionType.choice_text:
            return [(C.id, C.getText(language)) for C in self.getChoices()]
        elif self.type == QuestionType.yes_no:
            return [('true', 'Yes'), ('false', 'No')]

    def getAnswersInSubQuestion(self, surveyAnswer, answerGroup):
        return orm.select(A for A in db.Answer if A.surveyAnswer == surveyAnswer
                          and A.grouping == answerGroup
                          and A.question.type != QuestionType.group
                          and A.question == self).order_by(db.Answer.orderInSurveyAnswer)

    def getAnswersInSurveyAnswer(self, surveyAnswer):
        return orm.select(A for A in db.Answer if A.question == self and
                          A.surveyAnswer == surveyAnswer).order_by(lambda A: A.orderInSurveyAnswer)

    def can_have_multiple_answers(self):
        return self.type not in [QuestionType.note, QuestionType.yes_no, QuestionType.checkbox]

    def is_numeric_type(self):
        return self.type in [QuestionType.numeric, QuestionType.choice_numeric]

    def is_choice_type(self):
        return self.type in [QuestionType.choice_text, QuestionType.choice_numeric, QuestionType.l0_entity]
        
    def is_text_type(self):
        return self.type in [QuestionType.text, QuestionType.long_text]

    def is_system(self):
        system_questions = orm.select(question.question for question in db.OrderedQuestion if question.survey.form.is_system)
        return (self in system_questions)
    
    def duplicate(self, new_ref=None):
        duplicated_question = Question(
            name=self.name,
            slug=self.slug,
            type=self.type,
            updateDate=self.updateDate,
            version=self.version,
            usable=False,
            icon=self.icon,
            unit=self.unit,
            isInt=self.isInt,
            minValue=self.minValue,
            maxValue=self.maxValue,
            updatedBy=self.updatedBy
        )
        for text in self.text:
            duplicated_question.text.create(
                language=text.language,
                fullQuestion=text.fullQuestion,
                variableName=text.variableName
            )
        duplicated_question.usable = self.usable
        for choice in self.choices:
            duplicated_choice = duplicated_question.choices.create(
                value_numeric=choice.value_numeric,
                order=choice.order
            )
            for text in choice.text:
                duplicated_choice.text.create(
                    language=text.language,
                    value_text=text.value_text
                )
        orm.flush()
        return duplicated_question
                

    @classmethod
    @orm.db_session
    def last_version_by_name(cls, name):
        question = cls.select(
            lambda q: q.name == name
        ).order_by(orm.desc(cls.version)).first()
        return question.version if question else 0

    def _check_data_coherence(self):
        if not QuestionType.valid(self.type):
            raise ValueError
        forms = orm.select(q.survey.form for q in self.orderInSurvey)
        if forms.count() > 1:
            raise Exception('Question cannot be used in more than one form')
        if Question.select(lambda q: self != q and q.name == self.name and forms.first() in q.orderInSurvey.survey.form):
            raise Error(f'The name "{self.name}" is already used in another question in the same form')

    @classmethod
    def get_model_definition(cls, **kwargs):
        return {
            "properties": {
                'id': {
                    "type": "integer",
                    "example": 1234,
                    "value": lambda o: o.id,
                    "description": "This is the ID of the Question."
                },
                'type': {
                    "description": "This is the type of the Question",
                    "type": "string",
                    "enum": QuestionType.to_list(),
                    "example": "choice_numeric",
                    "value": lambda o: QuestionType.get_property_name_from_id(o.type) if not (QuestionType.get_property_name_from_id(o.type) == 'numeric' and o.isInt) else 'integer'
                },
                'slug': {
                    "description": "This is the slug of the Question",
                    "type": "text",
                    "example": "kids-name",
                    "value": lambda o: o.slug
                },
                'name': {
                    "description": "This is the name of the Question",
                    "type": "text",
                    "example": "Kids Name",
                    "value": lambda o: o.name
                },
                'text': {
                    "description": "This is the text of the Question",
                    "type": "text",
                    "example": "What is your kid's name?",
                    "value": lambda o: o.getText(1)
                },
                'icon': {
                    "description": "This is the icon of the Question",
                    "type": "text",
                    "example": "icon.png",
                    "value": lambda o: o.icon
                },
                'unit': {
                    "description": "This is the unit of the Question",
                    "type": "text",
                    "example": "unit.png",
                    "value": lambda o: o.unit
                },
                'min_value': {
                    "description": "This is the minValue of the Question",
                    "type": "integer",
                    "example": 0,
                    "value": lambda o: o.minValue
                },
                'max_value': {
                    "description": "This is the maxValue of the Question",
                    "type": "integer",
                    "example": 100,
                    "value": lambda o: o.maxValue
                },
                'choices': {
                    "description": "This is the choices of the Question",
                    "type": "array",
                    "items": {
                        "type": "text"
                    },
                    'value': lambda o: [choice[1] for choice in o.get_choices_list(1)] if o.get_choices_list(1) else []
                },
                'additional_data': {
                "description": "This is the additional data for the Question, either regex or picture data based on the question type",
                "type": "object",
                "oneOf": [
                    {
                        "properties": {
                            "regex": {
                                "type": "string",
                                "description": "Regular expression for validation (only for regex type questions)",
                                "example": "^[a-zA-Z0-9]+$"
                            }
                        },
                        "description": "JSON with regex field for regex question type"
                    },
                    {
                        "properties": {
                            "picture_type": {
                                "type": "string",
                                "description": "The type of picture required for the question (only for picture type questions)",
                                "enum": PictureType.to_list(),
                                "example": "generic"
                            },
                            "picture_instructions": {
                                "type": "string",
                                "description": "Instructions for the picture (optional for picture type questions)",
                                "example": "Upload a clear face picture."
                            }
                        },
                        "description": "JSON with picture_type and picture_instructions for picture question type"
                    }
                ],
                "value": lambda o: o.additional_data
            },
            },
            "create_required": [],
            "create_allowed": [],
            "edit_required": [],
            "edit_allowed": ["order"],
            "bulk_edit_allowed": ["id", "order"],
            "bulk_edit_required": ["id"],
            "bulk_view_allowed": [],
            "bulk_view_required": [],
            "view_required": [],
            "view_allowed": None
        }

