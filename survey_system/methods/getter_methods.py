from pony import orm


from survey_system.models.question_choice_text import QuestionChoiceText
from survey_system.models.ordered_question import OrderedQuestion
from survey_system.models.forms import FormVersion
from survey_system.models.answer import Answer


@orm.db_session
def get_all_surveys():
    return orm.select(s for s in FormVersion)

@orm.db_session
def getSurveyFromID(surveyId, version=None):
    if version is None:
        return orm.select(Q for Q in FormVersion if Q.id == surveyId) \
                      .order_by(lambda Q: orm.desc(Q.version)).first()
    else:
        return orm.select(Q for Q in FormVersion if Q.id == surveyId and Q.version == version)

@orm.db_session
def getQuestionInSurvey(questionnaire, questionName):
    return orm.select(Q for Q in OrderedQuestion if Q.survey == questionnaire and
                  Q.question.name == questionName).first()

@orm.db_session
def getQuestionChoiceFromQuestion(question, name):
    return orm.select(
        Qct for Qct in QuestionChoiceText if
        Qct.questionChoice.question.id == question.question.id and Qct.value_text == name).first()

@orm.db_session
def getQuestionChoiceFromId(id):
    return orm.select(Q for Q in QuestionChoiceText if Q.questionChoice.id == id).first()

def getAnswerToQuestionInSurveyAnswer(survey_answer, question_name, multiple=False):
    this_answer = orm.select(answer for answer in Answer
                             if answer.surveyAnswer == survey_answer
                             and answer.question.name == question_name)
    if not multiple:
        return this_answer.first()
    else:
        return this_answer
