from core_system.person.models.form_visibility import FormVisibilityRule, FormVisibilityScope, FormVisibility
from pony.orm import flush, commit
from survey_system.models.question_group import QuestionGroup
from survey_system.models.question_type import QuestionType
from survey_system.services.other_services import QuestionCreator
from survey_system.form_editor.services import FormService
from survey_system.models.forms import Form
from config import SYSTEM_SURVEYS_INFO, TEST_SURVEYS_INFO


def proccess_question_data(questions, data, order, grouping=None):
    question = QuestionCreator.create(data)
    flush()
    oqdata = {
        'question': question.id,
        'order': order,
        'min_answers': data.get('min_answers', 0),
        'max_answers': data.get('max_answers', 1),
        'grouping': grouping,
        'sub_question': bool(grouping)
    }
    if question.type == QuestionType.group:
        grouping = QuestionGroup()
        flush()
        oqdata.update({
            'grouping': grouping.id,
        })
        for subq in data.get('sub_questions'):
            order += 1
            questions, order = proccess_question_data(questions, subq, order, grouping=grouping.id)
    questions.append(oqdata)
    return questions, order


def create_all_system_surveys():
    create_all_surveys(SYSTEM_SURVEYS_INFO)


def create_all_test_surveys():
    create_all_surveys(TEST_SURVEYS_INFO)


def create_all_surveys(surveys):
    for survey in surveys:
        form = Form(name=survey['name'], icon=survey.get('icon'), is_system=True,
                                for_leads=survey.get('for_leads', True),
                                for_clients=survey.get('for_clients', True),
                                for_interactions=survey.get('for_interactions', True))
        questions = []
        order = 1
        for question_data in survey['questions']:
            questions, order = proccess_question_data(questions, question_data, order)
            order += 1
        for scope, status in survey.get('scopes', {}).items():
            FormVisibilityRule(
                order=order,
                status=getattr(FormVisibility, status),
                scope=getattr(FormVisibilityScope, scope),
                form=form
            )
        this_form = FormService.create(form, questions)
        commit()
        this_form.update_cached_data()

