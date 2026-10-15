from flask_login import login_required, current_user
from flask import render_template, request, abort
from pony.orm import db_session, desc

import config
if config.ENABLE_ENTERPRISE_FEATURES:
    from after_sales_system.interaction_system.services.discussed_topic_getter_service import DiscussedTopicGetterService
else:
    class _DiscussedTopicGetterServiceStub:
        @staticmethod
        def get_from_user_and_id(*_, **__):
            return None

    DiscussedTopicGetterService = _DiscussedTopicGetterServiceStub()
from . import custom_forms
from survey_system.services.survey_answer_getter_service import SurveyAnswerGetterService
from sales_system.leads.services.lead_getter_service import LeadGetterService
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from shared.helpers.select2 import render


@custom_forms.route('/answers/<int:survey_answer_id>/<action>', methods=['GET'])
@login_required
@db_session
def custom_forms_answers_views(survey_answer_id, action):
    lead_id = request.args.get('lead_id', None)
    discussed_topic_id = request.args.get('discussed_topic_id', None)
    lead = None
    if lead_id:
        lead = LeadGetterService.get_from_user_and_id(current_user, lead_id)
    this_form_answer = SurveyAnswerGetterService.get_from_user_and_id(current_user, survey_answer_id)
    if discussed_topic_id:
        discussed_topic = DiscussedTopicGetterService.get_from_user_and_id(current_user, discussed_topic_id)
    else:
        discussed_topic = None
    return render_template('custom_forms_render.html', render=action, this_form_answer=this_form_answer, lead=lead, discussed_topic=discussed_topic)

@custom_forms.route('/answers/history/<int:form_answer_id>', methods=['GET'])
@login_required
@db_session
def view_answer_history(form_answer_id):
    surveyAnswers = SurveyAnswerGetterService.get_all_versions_of_answer(form_answer_id)
    surveyAnswers = surveyAnswers.order_by(lambda x: desc(x.started)) if surveyAnswers else []
    if not surveyAnswers:
        return abort(404)
    firstAnswer = surveyAnswers.first()
    thisForm = firstAnswer.surveyAnswered
    if firstAnswer.lead_answering:
        if not current_user.can_access('ViewLeads', person=firstAnswer.lead_answering.person):
            return abort(403)
    elif firstAnswer.client_answering:
        if not current_user.can_access('ViewClients', person=firstAnswer.client_answering.person):
            return abort(403)
    return render_template(
        'view_answer_history.html',
        surveyAnswers=surveyAnswers,
        thisForm=thisForm
    )

@custom_forms.route('/l0_entities_source', methods=['GET'])
@login_required
@db_session
def get_l0_entities_ajax():
    l0_entities = OperationalEntitiesGetterService.get_list(current_user, level=0).order_by(lambda V: V.name)
    select2 = {
        'l0_entities': {
            'items': l0_entities,
            'text': 'name'
        }
    }
    return render(None, select2=select2)
