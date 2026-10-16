from datetime import datetime
from pony.orm import select, Json
from shared.helpers.db_helpers import Optional, PrimaryKey
from survey_system.models.answer import Answer
from data_system.analytical_db.analytical_db import analytical_db
from data_system.analytical_db.models.base_analytical_db_model import BaseAnalyticalDBModel
from survey_system.models.question_type import QuestionType
import config
import json


ENTERPRISE_FEATURES_ENABLED = getattr(config, "ENABLE_ENTERPRISE_FEATURES", False)


class Question_Answers(analytical_db.Entity, BaseAnalyticalDBModel):

    _description_ = 'This contains all the answers given to questions in custom forms. They are presented in a flattened form for convenience. The most common way to use them is to filter by the name of the question and perform statistics (average, repartition, etc.) on the answers given. '

    base_model = Answer

    id = PrimaryKey(int, comment="The internal unique ID of the answer")
    date = Optional(datetime, comment="The date at which the answer was given")
    filled_by_user_id = Optional("Users",  csv_columns=[("Filled by User Name", lambda l: l.full_name)], comment="The internal ID of the user who filled the form", column="filled_by_user_id")
    answered_by_client_id = Optional("Clients", csv_columns=[("Lead/Client Name", lambda l: l.full_name)], comment="The internal ID of the client who answered the question", column="answered_by_client_id")
    answered_by_lead_id = Optional("Leads", csv_columns=[("Lead/Client Name", lambda l: l.full_name)], comment="The internal ID of the lead who answered the question", column="answered_by_lead_id")
    # Link to interactions only exists in enterprise edition. In OSS mode keep
    # this as a plain integer so Pony doesn't require the Interactions entity.
    if ENTERPRISE_FEATURES_ENABLED:
        interaction_id = Optional("Interactions", comment="The internal ID of the interaction during which the answer was provided (if any)", column="interaction_id")
    else:
        interaction_id = Optional(int, comment="The internal ID of the interaction during which the answer was provided (if any)", column="interaction_id")

    form_id = Optional(int, comment="The internal ID of the form to which the answer belongs")
    form_name = Optional(str, comment="The name of the form to which the answer belongs")
    question_id = Optional(int, comment="The internal ID of the question answered")
    question_name = Optional(str, comment="The name of the question answered")

    answer_value_text = Optional(str, comment="The text of the answer (if applicable)")
    answer_value_numeric = Optional(float, comment="The numeric value of the answer (if applicable)")
    answer_value_datetime = Optional(datetime, comment="The datetime value of the answer (if applicable)")
    answer_value_picture_uuid = Optional(str, comment="The UUID of the picture of the answer (if applicable). The actual picture can be retreived using the API (see API documentation for more details)")

    answer_value_gps_longitude = Optional(float, comment="The WGS84 longitude value recorded for the answer (if GPS question)", precision=4)
    answer_value_gps_latitude = Optional(float, comment="The WGS84 latitude value recorded for the answer (if GPS question)", precision=4)
    answer_value_json = Optional(Json, comment="The JSON value of the answer for GPS coordinates for crop mapping (if applicable)")

    is_last_answer = Optional(bool, comment="True if this is the last answer for the question (the person did not answer this question in a later interaction)")
    is_first_answer = Optional(bool, comment="True if this is the first answer for the question (the person did not answer this question in a previous interaction)")

    # Internal
    last_updated = Optional(datetime, comment=config.LAST_UPDATED_DEFINITION)

    @staticmethod
    def converter(answer):
        coords = answer[9].split(';') if answer[18] == QuestionType.gps else None
        return {
            'id': answer[0],
            'filled_by_user_id': answer[1] if answer[1] else None,
            'answered_by_client_id': answer[2].id if answer[2] else None,
            'answered_by_lead_id': answer[3].id if answer[3] else None,
            # Interaction is only available when enterprise features are enabled.
            'interaction_id': (
                answer[4].discussed_topic.interaction.id
                if ENTERPRISE_FEATURES_ENABLED
                and answer[4].discussed_topic
                and answer[4].discussed_topic.interaction
                else None
            ),
            'form_id': answer[5],
            'form_name': answer[6],
            'question_id': answer[7],
            'question_name': answer[8],
            'answer_value_text': answer[9] or '',
            'answer_value_numeric': answer[10],
            'answer_value_datetime': answer[11],
            'answer_value_picture_uuid': answer[17].uuid if answer[17] else '',
            'date': answer[12],
            'answer_value_gps_longitude': float(coords[0]) if coords and coords[0] not in ['', 'None'] else None,
            'answer_value_gps_latitude': float(coords[1]) if coords and coords[1] not in ['', 'None'] else None,
            'is_last_answer': answer[15],
            'is_first_answer': answer[16],
            'last_updated': answer[19],
            'answer_value_json': json.dumps(answer[20]) if answer[18] == QuestionType.gps_surface else "{}"
        }

    @staticmethod
    def selector(objects):
        return select((
            s.id,
            s.surveyAnswer.interviewer.user.id,
            s.surveyAnswer.client_answering,
            s.surveyAnswer.lead_answering,
            s.surveyAnswer,
            s.surveyAnswer.surveyAnswered.id,
            s.surveyAnswer.surveyAnswered.form.name,
            s.question.id,
            s.question.name,
            s.value_text,
            s.value_numeric,
            s.value_date,
            s.surveyAnswer.started,
            s.surveyAnswer.surveyMethod,
            s.orderInSurveyAnswer,
            s.surveyAnswer.is_last_answer,
            s.surveyAnswer.is_first_answer,
            s.value_stored_file,
            s.question.type,
            Question_Answers.extended_modified_date(s),
            s.value_json
        ) for s in objects).order_by(20)

    @staticmethod
    def extended_modified_date(obj):
        return max(obj.modifiedDate, obj.surveyAnswer.modifiedDate, obj.surveyAnswer.surveyAnswered.modifiedDate)