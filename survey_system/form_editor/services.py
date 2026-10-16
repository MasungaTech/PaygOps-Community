from curses import flushinp
from survey_system.models.question_group import QuestionGroup
from werkzeug.exceptions import NotFound
from shared.logger.loggers import Error
from pony import orm

from datetime import datetime

from shared.api_helpers.client_helpers.api_exceptions import ObjectDoesNotExist
from survey_system.form_editor.form_validator import FormValidator
from survey_system.models.ordered_question import OrderedQuestion
from survey_system.models.question import Question
from survey_system.services.form_getter_service import FormVersionGetterService
from survey_system.services.form_version_edit_service import FormVersionEditService
from survey_system.services.other_services import QuestionService
from survey_system.models.forms import FormVersion
from shared.services.sorter import Sorter
from shared.helpers.form_helpers import value_to_bool


class FormSorter(Sorter):
    def sort_by(field_name):
        options = {
            'id': lambda s: s.id,
            'name': lambda s: s.name,
            'nb_answers': lambda s: s.nb_answers,
        }
        return options.get(field_name, lambda s: s.id)


class FormService:

    @classmethod
    def get_non_system_forms(cls):
        return orm.select(version for version in FormVersion if version.form.is_system is False)

    @classmethod
    def validate(cls, body_data, just_questions=False, questions_required=True):
        if not (cls._check_if_system_by_data(body_data)):
            FormValidator(body_data).is_valid(just_questions=just_questions, questions_required=questions_required)

    @classmethod
    def create(cls, form, questions, user=None):
        form_version = cls._create_version(form, user)
        FormVersionEditService._add_questions(form_version, questions)
        form_version.update_cached_data()
        return form_version

    @classmethod
    @orm.db_session
    def _create_version(cls, form, user=None):
        return FormVersion(
            form=form,
            version=1 if not form.versions.count() else form.last_version_number+1,
            updatedBy=user
        )

    @classmethod
    def _check_if_system_by_data(cls, data):
        name = data.get('name')
        version = orm.select(version for version in FormVersion if version.form.name == name).order_by(FormVersion.id).first()
        return version.form.is_system if version else False

    @classmethod
    def retrieve(cls, user, form_id):
        form = cls._retrieve_form_by_id(user, form_id)
        formatted_form = cls._formatted_form(form)

        ordered_questions = cls._retrieve_ordered_questions(form_id)
        formatted_ordered_questions = cls._format_ordered_questions(ordered_questions)

        response = cls._create_response(formatted_form, formatted_ordered_questions)

        return response

    @staticmethod
    def _retrieve_form_by_id(user, form_id):
        return FormVersionGetterService.get_from_user_and_id(user, form_id, strict=True, main_resource=True)

    @staticmethod
    def _formatted_form(version):
        return dict(id=version.id, name=version.form.name, icon=version.form.icon, version=version.version)

    @staticmethod
    def _retrieve_ordered_questions(form_id):
        ordered_questions = orm.select(ord_question for ord_question in OrderedQuestion if ord_question.survey.id == form_id)

        return ordered_questions

    @staticmethod
    def _format_ordered_questions(ordered_questions):
        formatted_ordered_questions = list()
        for ord_question in ordered_questions:
            formatted_questions = dict(
                id=ord_question.question.id,
                name=ord_question.question.name)
            formatted_ordered_questions.append(
                {
                    'order': ord_question.order,
                    'min_answers': ord_question.minAnswers,
                    'max_answers': ord_question.maxAnswers,
                    'protected': ord_question.protected,
                    'question': formatted_questions,
                    'group': ord_question.grouping.id if ord_question.grouping else None,
                    'multi': QuestionService.question_is_multi_type(ord_question.question.type),
                    'not_required': QuestionService.question_cannot_be_required(ord_question.question.type)
                }
            )

        return formatted_ordered_questions

    @staticmethod
    def _create_response(form, ordered_questions):
        form['questions'] = ordered_questions
        return form

    @classmethod
    def update(cls, user, form_id, data):
        old_form_obj = cls._retrieve_form_by_id(user, form_id)
        old_form = old_form_obj.to_dict(with_lazy=True)

        old_form.pop('id')
        old_form.pop('mobile_uuid')
        old_form['version'] = old_form_obj.form.versions.select().order_by(lambda s: orm.desc(s.version)).first().version + 1
        new_form = FormVersion(**old_form)

        updated_form = cls._update_old_form(new_form, data, form_id)
        updated_form.update_cached_data()
        return updated_form.to_dict()

    @classmethod
    def patch(cls, form, data, op=None):
        op = op or 'edit'
        model_schema = form.get_model_schema(op)
        for prop, schema in model_schema['properties'].items():
            if prop not in data:
                continue
            value = value_to_bool(data[prop]) if schema['type'] == 'boolean' else data[prop]
            setattr(form, prop, value)
    
    @classmethod
    def _update_old_form(cls, form, data, form_id):
        form.updateDate = datetime.now()
        form.questions = cls._new_ordered_questions(form_id, data.get('questions'))
        return form

    @classmethod
    def _new_ordered_questions(cls, form_id, ord_question_data):
        ordered_questions_list = list()

        for ord_question in ord_question_data:
            question = Question.get(id=ord_question.get('question'))
            ordered_questions_list.append(
                OrderedQuestion(
                    question=question,
                    order=ord_question.get('order'),
                    survey=form_id,
                    minAnswers=ord_question.get('min_answers'),
                    maxAnswers=ord_question.get('max_answers'),
                    protected=ord_question.get('protected')
                )
            )

        return ordered_questions_list

    @staticmethod
    def is_in_use(version):
        return version.form.visibility_rules.count() or version.interactionTopic.count()

    @classmethod
    def delete_version(cls, version):
        FormVersionEditService._delete_from_object_and_user(version)

    @classmethod
    def delete_form(cls, form):
        for version in form.versions:
            FormVersionEditService._delete_from_object_and_user(version)
