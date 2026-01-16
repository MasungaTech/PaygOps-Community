from pony.orm import db_session

from survey_system.models.languages import Languages
from survey_system.models.question_type import QuestionType

def getQuestionTypeName(typeID):
    statusNames = {}
    statusNames[0] = "group"
    statusNames[1] = "yes_No"
    statusNames[2] = "text"
    statusNames[3] = "numeric"
    statusNames[4] = "choice_Text"
    statusNames[5] = "choice_Numeric"
    statusNames[6] = "picture"
    statusNames[7] = "long_Text"
    statusNames[8] = "checkbox"
    statusNames[9] = 'date'
    statusNames[10] = 'note'
    statusNames[11] = 'gps'
    statusNames[12] = 'url'
    statusNames[13] = 'signature'
    statusNames[14] = 'gps_surface'
    statusNames[15] = 'regex'
    statusNames[16] = 'l0_entity'
    return statusNames[typeID]


@db_session
def getQuestionStructure(thisSurvey, Questions=None, toDict=False, includeQuestionData=False):
    if Questions is None:
        Questions = thisSurvey.getQuestions()

    surveyQuestions = []

    for i, Q in enumerate(Questions):

        if toDict:
            question = getQuestionData(Q)
            surveyQuestions.append(question)

        else:
            question = Q

            if Q.getType() == QuestionType.group:
                surveyQuestions.append(getQuestionStructure(thisSurvey, Q.getSubQuestions(), toDict, includeQuestionData))
            else:
                surveyQuestions.append(question)

    return surveyQuestions


@db_session
def getQuestionData(thisOrderedQuestion, language=Languages.english):
    Q = mobileQuestion()
    Q.id = thisOrderedQuestion.id

    Q.name = thisOrderedQuestion.question.name
    Q.icon = thisOrderedQuestion.question.icon

    Q.questionText = thisOrderedQuestion.getText(language)
    Q.variableName = thisOrderedQuestion.getVariableName(language)

    Q.type = getQuestionTypeName(thisOrderedQuestion.question.type)
    Q.unit = thisOrderedQuestion.question.unit
    Q.isInt = thisOrderedQuestion.question.isInt

    Q.minValue = thisOrderedQuestion.question.minValue
    Q.maxValue = thisOrderedQuestion.question.maxValue

    Q.minAnswers = thisOrderedQuestion.minAnswers
    Q.maxAnswers = thisOrderedQuestion.maxAnswers

    Q.protected = thisOrderedQuestion.protected

    Q.additionalData = thisOrderedQuestion.question.additional_data

    if thisOrderedQuestion.question.type == QuestionType.group:
        Q.subQuestions = []
        subQuestions = thisOrderedQuestion.getSubQuestions()
        for S in subQuestions:
            Q.subQuestions.append(getQuestionData(S))

    elif thisOrderedQuestion.question.type == QuestionType.choice_text:
        Q.choices = []
        questionChoices = thisOrderedQuestion.getChoices()
        for C in questionChoices:
            Q.choices.append({'id': C.id, 'value': C.getText(language)})

    elif thisOrderedQuestion.question.type == QuestionType.choice_numeric:
        Q.choices = []
        questionChoices = thisOrderedQuestion.getChoices()
        for C in questionChoices:
            Q.choices.append({'id': C.id, 'value': C.getValue()})

    return Q.__dict__


class mobileQuestion():
    id = None
    name=None
    icon = None

    questionText=None
    variableName=None

    type = None
    unit = None
    minValue = None
    maxValue = None
    minAnswers = None
    maxAnswers = None

    protected = False

    subQuestions = [] # List of dict each with a subquestion
    choices = [] # List of dict, with ID and Value
    isInt = None # For numeric type
    additionalData = None;
