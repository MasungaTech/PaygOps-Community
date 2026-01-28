from shared.api_helpers.model_definition_base import ModelDefinitionMixin
from pony import orm
from core_system.core_entities import db
from survey_system.models.question_group import QuestionGroup
from survey_system.models.question_type import PictureType, QuestionType
from constants import INTEGER_OPTIONAL_OPTIONS_STRING, NULL_OPTION



class OrderedQuestion(db.Entity, ModelDefinitionMixin):
    question = orm.Required('Question', column="question")
    order = orm.Required(int)
    survey = orm.Optional('FormVersion', column="survey")
    grouping = orm.Optional(QuestionGroup, column="grouping")
    isSubQuestion = orm.Required(bool, default=False)
    minAnswers = orm.Required(int, default=0)
    maxAnswers = orm.Optional(int, default=1)
    protected = orm.Required(bool, default=False)


    def after_insert(self):
        self.question.update_related_survey_cache()

    def after_update(self):
        self.question.update_related_survey_cache()

    def getUnit(self):
        return self.question.unit

    def getSubQuestions(self):
        return self.grouping.getSubQuestions() if self.grouping else []

    def getMinValue(self):
        return self.question.minValue

    def getMaxValue(self):
        return self.question.maxValue

    def isInt(self):
        return self.question.isInt

    def isRequired(self):
        return self.minAnswers > 0

    def getType(self):
        return self.question.type

    def getIcon(self):
        return self.question.icon

    def multipleAnswersAllowed(self):
        if self.maxAnswers and (self.maxAnswers > 1):
            return True
        elif not self.maxAnswers:
            return True
        else:
            return False

    def getText(self, language):
        return self.question.getText(language)

    def getVariableName(self, language):
        return self.question.getVariableName(language)

    def getChoices(self):
        return self.question.getChoices()

    def get_choices_list(self, language):
        return self.question.get_choices_list(language)

    def getAnswersInSubQuestion(self, surveyAnswer, orderInSurveyAnswer):
        return self.question.getAnswersInSubQuestion(surveyAnswer, orderInSurveyAnswer)

    def getAnswersInSurveyAnswer(self, surveyAnswer):
        return self.question.getAnswersInSurveyAnswer(surveyAnswer)

    def getRegex(self):
        return self.question.additional_data.get('regex') if self.question.additional_data else None
    
    @staticmethod
    def person_in_household_question_ids():
        return orm.select(oq.question.id for oq in OrderedQuestion
                          if oq.question.name == 'nb_adults'
                          or oq.question.name == 'nb_child')

    @classmethod
    def get_model_definition(cls, new_models=False, for_export=False,**kwargs):
        definition = {
            "properties": {
                'id': {
                    "type": "integer",
                    "example": 1234,
                    "value": lambda o: o.id,
                    "description": "This is the ID of the Ordered Question. "
                },
                'order': {
                    "description": "This is order of the Ordered Question in the form.",
                    "type": "integer",
                    "example": 2,
                    "value": lambda o: o.order
                }
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
            "view_allowed": []
        }
        if new_models:
            del definition['properties']['id']
            del definition['properties']['order']
            definition['properties'].update({
                'id': {
                    "type": "integer",
                    "example": 1234,
                    "value": lambda o: o.question.id,
                    "description": "This is the ID of the Question. When editing a form, you can specify the ID of the question to use it, if not specified it is assumed that it is a new question. WARNING: You cannot pass both the ID and questions parameters at once. "
                },
                'slug': {
                    "description": "This is the slug of the Question",
                    "type": "string",
                    "example": "kids-name",
                    "value": lambda o: o.question.slug
                },
                'name': {
                    "description": "This is the name of the Question",
                    "type": "string",
                    "example": "Kids Name",
                    "value": lambda o: o.question.name
                },
                'text': {
                    "description": "This is the text of the Question",
                    "type": "string",
                    "example": "What is your kid's name?",
                    "value": lambda o: o.question.getText(1)
                },
                'icon': {
                    "description": "This is the icon of the Question. It should use Google's Material Symbols name. ",
                    "type": "string",
                    "example": "home",
                    "value": lambda o: o.question.icon
                },
                'type': {
                    "description": "This is the type of the Question",
                    "type": "string",
                    "enum": QuestionType._get_options_list(),
                    "example": "choice_text",
                    "value": lambda o: QuestionType.get_property_name_from_id(o.question.type) if not (QuestionType.get_property_name_from_id(o.question.type) == 'numeric' and o.question.isInt) else 'integer'
                },
                'min_value': {
                    "description": "This is the minimum value of the Question. For a text question it's the minimum number of characters.",
                    'schema': {
                        'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING
                    },
                    "example": 0,
                    "value": lambda o: o.question.minValue
                },
                'max_value': {
                    "description": "This is the maximum value of the Question. For a text question it's the maximum number of characters.",
                    'schema': {
                        'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING
                    },
                    "example": 100,
                    "value": lambda o: o.question.maxValue
                },
                'unit': {
                    "description": "This is the unit of the Question (for numeric questions only)",
                    "type": "string",
                    "example": "kWh",
                    "value": lambda o: o.question.unit
                },
                'choices': {
                    "description": "These are the choices of the Question (for choice questions only)",
                    "type": "array",
                    "items": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "number"}
                        ]
                    },
                    "example": ["Alex", "Ben", "Jeff"],
                    'value': lambda o: [choice[1] for choice in o.question.get_choices_list(1)] if o.question.get_choices_list(1) else []
                },
                'min_answers': {
                    "description": "This is the minimum number of answers required for the Question. If set to **>0 (or >=1)** the question will be required.",
                    'schema': {
                        'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING
                    },
                    "example": 1,
                    "value": lambda o: o.minAnswers
                },
                'max_answers': {
                    "description": "This is the maximum number of answers allowed for the Question.",
                    'schema': {
                        'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING
                    },
                    "example": 1,
                    "value": lambda o: o.maxAnswers
                },
                'group': {
                    "description": "This is the group of the Question. When creating a form, put any group ID here to create a group and put the same number on the group questions and the questions part of the group. The group will automatically be created and assigned an ID after creation.",
                    'schema': {
                        'oneOf': INTEGER_OPTIONAL_OPTIONS_STRING
                    },
                    "example": 1,
                    "value": lambda o: o.grouping.id if o.grouping else None
                },
                'protected': {
                    "description": "This is the protection status of the Question. If true, the question will only be answereable by someone with the permission to answer protected questions.",
                    "type": "boolean",
                    "example": True,
                    "value": lambda o: o.protected
                },
                'additional_data': {
                "description": "This is the additional data for the Question, either regex or picture data based on the question type",
                "oneOf": [
                    {
                        "type": "object",
                        "properties": {
                            "regex": {
                                "type": "string",
                                "description": "Regular expression for validation (only for regex type questions)",
                                "example": "^[a-zA-Z0-9]+$"
                            }
                        },
                        "required": ["regex"],
                        "description": "JSON with regex field for regex question type"
                    },
                    {
                        "type": "object",
                        "properties": {
                            "picture_type": {
                                "type": "string",
                                "description": "The type of picture required for the question (only for picture type questions)",
                                "enum": PictureType._get_options_list(),
                                "example": PictureType.face_picture
                            },
                            "picture_instructions": {
                                "type": "string",
                                "description": "Instructions for the picture (optional for picture type questions)",
                                "example": "Upload a clear face picture."
                            }
                        },
                        "required": ["picture_type"],
                        "description": "JSON with picture_type and picture_instructions for picture question type"
                    },
                ]+NULL_OPTION,
                "value": lambda o: o.question.additional_data if o.question.additional_data else None
            },
            })
            if for_export:
                del definition['properties']['id']
        return definition
