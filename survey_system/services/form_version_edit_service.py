from shared.logger.loggers import Error
from shared.services.base_service import BaseService
from survey_system.models.forms import FormVersion, Form
from survey_system.services.other_services import QuestionCreator
from survey_system.models.ordered_question import OrderedQuestion
from survey_system.models.question_group import QuestionGroup
from survey_system.models.question_type import QuestionType
from survey_system.models.question import Question
from shared.api_helpers.client_helpers.uuid_generation_helpers import generate_uuid
from constants import AVAILABLE_ICONS


class FormVersionEditService(BaseService):

    @classmethod
    def _add_from_data_and_user(cls, data_dict, user):
        form_id = data_dict.get('form_id')
        if form_id:
            form = Form.get(id=form_id)
            if not form:
                raise Error('Form not found.')
            # We update the form with the new data
            cls._edit_from_data_and_user(form=form, data_dict=data_dict, user=user)
        else:
            if data_dict.get('icon') and data_dict.get('icon') not in AVAILABLE_ICONS:
                raise Error(f"The icon '{data_dict.get('icon')}' does not exist")
            form = Form(
                name=data_dict.get('name'),
                icon=data_dict.get('icon', ''),
                for_leads=data_dict.get('available_for_leads', True),
                for_clients=data_dict.get('available_for_clients', True),
                for_interactions=data_dict.get('available_for_interactions', True),
            )
        form_version = FormVersion(
            form=form,
            mobile_uuid=data_dict.get('uuid', generate_uuid()),
            version=1 if not form.versions.count() else form.last_version_number+1,
            updatedBy=user
        )
        cls._add_questions(form_version, data_dict.get('questions', []))
        form_version.update_cached_data()
        return form_version

    @classmethod
    def _edit_from_data_and_user(cls, form_version=None, data_dict=None, user=None, form=None):
        if not form:
            form = form_version.form
        # We update the form with the new data
        form.name = data_dict.get('name')
        form.icon = data_dict.get('icon')
        form.available_for_leads = data_dict.get('available_for_leads')
        form.available_for_clients = data_dict.get('available_for_clients')
        form.available_for_interactions = data_dict.get('available_for_interactions')

    @classmethod
    def _add_questions(cls, form_version, questions):
        order = 0
        groups = {}
        groups_main_questions = {}
        names = []
        slugs = []
        for question_data in questions:
            order += 1
            grouping = None
            sub_question = False
            # We get or create the question object
            question_id = question_data.get('id', question_data.get('question'))
            if question_id:
                if question_data.get('id'): # Only if we use the new API, the old one was using the name 'question'
                    for key in question_data.keys():
                        if key != 'id':
                            raise Error(f'You cannot pass both the question ID and question parameters at once, if you want to copy a form without the IDs use the `for_export` query parameter when getting it. ')
                question = Question.get(id=question_id)
                if not question:
                    raise Error(f'No question found with id "{question_id}"')
                # If the question is already used in another form, we duplicate it
                first_appearance = question.orderInSurvey.select().first()
                if first_appearance and first_appearance.survey.form != form_version.form:
                    question = question.duplicate()
            else:
                question = QuestionCreator.create_question_from_api_data(question_data)
            # We check if the question name is already in the form version to avoid confusions
            if Question.select(lambda q: question != q and q.name == question.name and form_version in q.orderInSurvey.survey) or question.name in names:
                raise Error(f'A question with the name {question.name} already exists in this form, use the ID of the question to use it.')
            if Question.select(lambda q: question != q and q.slug == question.slug and form_version in q.orderInSurvey.survey) or question.slug in slugs:
                raise Error(f'A question with the slug {question.slug} already exists in this form, use the ID of the question to use it.')
            names += [question.name]
            slugs += [question.slug]
            # We handle the question groups if any
            group = question_data.get('group', question_data.get('grouping'))
            if group is not None:
                grouping = groups.get(group)
                if not grouping:
                    # We create the group if subquestions
                    grouping = QuestionGroup()
                    groups[group] = grouping
                if question.type != QuestionType.group:
                    sub_question = True # Automatically put sub-quesiton if needed
                else:
                    if group in groups_main_questions:
                        raise Error(f'The group {group} has more than one group question, you cannot have more than one group question in a group.')
                    groups_main_questions[group] = question
            # We then create the ordered question object
            ordered_question = OrderedQuestion(survey=form_version,
                                               question=question,
                                               order=question_data.get('order', order),
                                               minAnswers=question_data.get('min_answers', 0),
                                               maxAnswers=question_data.get('max_answers', 1),
                                               protected=question_data.get('protected', False),
                                               grouping=grouping,
                                               isSubQuestion=sub_question)
        # We then check that each group has only one main question
        for group in groups:
            if group not in groups_main_questions:
                raise Error(f'The group {group} has no main question, you need to add one or remove all questions from the group.')
    @classmethod
    def _delete_from_object_and_user(cls, form_version, user=None):
        form = form_version.form
        if form_version.in_settings:
            raise Error(f'Cannot delete form "{form.name}", it was used (at least once) in the settings')
        if form_version.answers.count():
            raise Error(f'Cannot delete form "{form.name}", it has answers')
        for oq in form_version.questions:
            question = oq.question
            oq.delete()
            if question.orderInSurvey.is_empty():
                question.delete()
        form_version.delete()
        if not form.versions.select().count():
            form.delete()
        return {'success': True}, 204