from core_system.users.services.current_user_service import get_current_api_user
from payg_loan_system.offers.services.list_offer_service import ListOfferService
from sales_system.leads.models.status_category import StatusCategory
from payg_loan_system.offers.models import Offer
from shared.services.celery_queue_service import CeleryQueueService
from survey_system.services.form_getter_service import FormGetterService, FormVersionGetterService
from worker_app.tasks.update_lead_statuses import update_lead_statuses
from survey_system.models.question_group import QuestionGroup
from pony.orm.core import flush
from core_system.person.models.form_visibility import FormVisibilityRule, FormVisibilityScope
from survey_system.models.forms import Form
from survey_system.models.question_type import QuestionType
from pony import orm
from werkzeug.exceptions import BadRequest
from flask_restful import Resource, request

from shared.logger.loggers import LogAPI, Error
from shared.api_helpers.server_helpers.jwt_and_schema_verification import verify

from survey_system.form_editor.services import FormService
from survey_system.services.other_services import QuestionService, Question
from shared.api_helpers.documented_resource import DocumentedResource
from survey_system.services.ai_form_creation_service import AIFormCreationService
from shared.services.audit_log_service import AuditLogService

log_api = LogAPI()


class FormListAPI(Resource):
    form_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "ai_creation_prompt": {"type": "string"},
            "icon": {"type": "string"},
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "order": {"type": "integer", "minimum": 0},
                        "question": {"type": "integer", "minimum": 0},
                        "min_answers": {"type": "integer", "minimum": 0, "default": 0},
                        "max_answers": {"type": "integer", "minimum": 0, "default": 1}
                    },
                    "required": ["order", "question", "min_answers", "max_answers"]
                }
            },
            "from_version": {"type": "integer"}
        },
        "oneOf": [
            {"required": ["name", "questions"]},
            {"required": ["from_version"]}
        ],
    }

    @verify(permissions=['ViewForms'])
    @orm.db_session
    def get(self):
        forms = Form.select() if not request.args.get('for_interactions', 'false') == 'true' else Form.select(lambda f: f.for_interactions)
        return [form.get_serialized_object() for form in forms]

    @verify(permissions=['AddForms'], schema=form_schema)
    @orm.db_session
    def post(self):
        name = request.json.get('name')
        icon = request.json.get('icon')
        questions = request.json.get('questions')
        if "from_version" in request.json:
            old_version = FormVersionGetterService.extract_from_user_and_id(get_current_api_user(), request.json, 'from_version', strict=True, empty_allowed=False)
            name = old_version.form.name + ' Copy'
            icon = old_version.form.icon
            grouping_data = {}
            questions = [{
                'question': q.question.duplicate().id,
                'order': q.order,
                'min_answers': q.minAnswers,
                'max_answers': q.maxAnswers,
                'grouping': get_grouping_data(grouping_data, q.grouping).id if q.grouping else None,
                'sub_question': q.isSubQuestion
            } for q in old_version.questions]
        elif "questions_required" in request.json and request.json["questions_required"] is False:
            FormService.validate(request.json, questions_required=False)
        else:
            FormService.validate(request.json)
        
        # Here we can process with the AI assitant
        ai_prompt = request.json.get('ai_creation_prompt')
        if ai_prompt:
            import config
            if not config.AI_ENABLED():
                raise Error("AI features are disabled. Please set the ANTHROPIC_API_KEY environment variable to enable AI features.")
            form_version = AIFormCreationService.create_form(ai_prompt, name, get_current_api_user())
        else:
            form = Form(name=name, icon=icon)
            form_version = FormService.create(form, questions, user=get_current_api_user())
        return form_version.get_serialized_object(new_models=False), 201


class FormAPI(DocumentedResource):

    PUBLIC = False

    @verify(permissions=['ViewForms'])
    @orm.db_session
    def get(self, form_id):
        form = FormService.retrieve(get_current_api_user(), form_id)
        return form, 200

    @verify(permissions=['EditForms'])
    @orm.db_session
    def put(self, form_id):
        body = request.json

        FormService.validate(body)
        form = FormService.update(get_current_api_user(), form_id, body)
        return form, 200

    @verify(permissions=['EditForms'])
    @orm.db_session
    def patch(self, form_id):
        form = FormGetterService.get_from_user_and_id(get_current_api_user(), form_id, strict=True, main_resource=True)
        data = request.json
        if not form.versions and (data.get('for_leads') or data.get('for_clients') or data.get('for_interactions')):
            raise Error('Form availability cannot be edited until you complete the form creation')
        FormService.patch(form, data)
        return form.get_serialized_object(), 200

    @verify(permissions=['EditForms'])
    @orm.db_session
    def post(self, form_id):
        form = FormGetterService.get_from_user_and_id(get_current_api_user(), form_id, strict=True, main_resource=True)
        FormService.validate(request.json, just_questions=True)
        form_version = FormService.create(form, request.json.get('questions'), user=get_current_api_user())

        AuditLogService.store_audit_log_data(
                    user=get_current_api_user(), 
                    data=request.json, 
                    action='add', 
                    object=form_version
                )
        
        return form.get_serialized_object(), 200


    @verify(permissions=['DeleteForms'])
    @orm.db_session
    def delete(self, form_id):
        form = FormGetterService.get_from_user_and_id(get_current_api_user(), form_id, strict=True, main_resource=True)
        FormService.delete_form(form)
        return {'success': True}, 204

    @classmethod
    def get_meta(cls):
        return {
            'patch': {
                "tags": ['Custom Forms'],
                "summary": "PATCH Form Object",
                "requestBody": {
                    "description": "Form Model with at least the required properties",
                    "schema": Form.get_model_schema(op="edit")
                }
            }
        }


class QuestionListAPI(Resource):
    @verify(permissions=['ViewForms'])
    @orm.db_session
    def get(self):
        note_question_type = 10

        non_system_questions = QuestionService.get_non_system_questions()
        questions = orm.select((question.id, question.name, question.version, question.type)
                               for question in non_system_questions if question.type != QuestionType.group
                               ).order_by(lambda: question.name)
        formatted_questions = [dict(id=question[0], name=question[1],
                                    display_name='[Custom] '+question[1]+' v'+str(question[2])+'',
                                    multi=QuestionService.question_is_multi_type(question[3]),
                                    not_required=QuestionService.question_cannot_be_required(question[3]))
                               for question in questions]
        system_questions = orm.select((question.id, question.name, question.version, question.type)
                                      for question in Question if question not in non_system_questions
                                      and question.type != QuestionType.group).order_by(lambda: question.name)
        formatted_questions += [dict(id=question[0], name=question[1],
                                    display_name='[Predefined] '+question[1]+' v'+str(question[2])+'',
                                     multi=QuestionService.question_is_multi_type(question[3]),
                                     not_required=QuestionService.question_cannot_be_required(question[3]))
                                for question in system_questions]
        return formatted_questions, 200

SCOPES = {
    "leads": FormVisibilityScope.lead_only,
    "clients": FormVisibilityScope.client_only
}

class FormsConfiguration(Resource):

    @verify(permissions=['EditForms'])
    @orm.db_session
    def put(self):
        i = 0
        configs = []
        for form_data in request.json.get('forms', []):
            i += 1
            form = FormGetterService.get_from_user_and_id(get_current_api_user(), form_data['id'], strict=True)
            if not form_data.get('scope'):
                raise Error(f'Scope missing for form {form.name}')
            if not form_data.get('status'):
                raise Error(f'Status (visibility) missing for form {form.name}')
            config = orm.select(r for r in form.visibility_rules if r.scope == form_data['scope']).first()
            offer_type = form_data['offer_type']
            offers_ids = form_data.get('offers', []) if offer_type in [None, 'specific'] else []
            if offer_type == 'specific':
                offer_type = ''
            if not config:
                config = FormVisibilityRule(
                    order=i,
                    status=form_data['status'],
                    scope=form_data['scope'],
                    answer_for_each_lead=form_data.get('answer_for_each_lead', False),
                    offer_type=offer_type,
                    form=form
                )
            else:
                config.order = i
                config.status = form_data['status']
                config.scope = form_data['scope']
                config.answer_for_each_lead=form_data.get('answer_for_each_lead', False)
                config.offer_type = offer_type
            for offer_id in offers_ids:
                offer = ListOfferService.get_from_user_and_id(get_current_api_user(), offer_id, strict=True)
                config.offers.add(offer)
            config.offers.remove(config.offers.select(lambda o: o.id not in offers_ids))
            flush()
            configs.append(config.id)

        to_delete = FormVisibilityRule.select(lambda c: c.id not in configs)
        for config in to_delete:
            config.delete()
        CeleryQueueService.execute_task(update_lead_statuses, status_categories=[StatusCategory.awaiting_decision, StatusCategory.awaiting_information])

def get_grouping_data(data, old_group):
    if not old_group in data:
        data[old_group] = QuestionGroup()
        flush()
    return data[old_group]


class FormVersionAPIOld(DocumentedResource):

    PUBLIC = False

    @verify(permissions=['ViewForms'])
    @orm.db_session
    def get(self, version_id):
        version = FormVersionGetterService.get_from_user_and_id(get_current_api_user(), version_id, strict=True, main_resource=True)
        return version.get_serialized_object(), 200

    @verify(permissions=['DeleteForms'])
    @orm.db_session
    def delete(self, version_id):
        version = FormVersionGetterService.get_from_user_and_id(get_current_api_user(), version_id, strict=True, main_resource=True)
        FormService.delete_version(version)
        return {'success': True}, 204
