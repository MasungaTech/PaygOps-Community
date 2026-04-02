import math
from core_system.users.services.current_user_service import get_current_api_user
from survey_system.models.question_choice import QuestionChoice
from survey_system.models.question_type import QuestionType
from pony import orm
from flask import request
from flask_restful import Resource, NotFound
from survey_system.services.other_services import QuestionCreator, QuestionService
from survey_system.models.forms import FormVersion
from survey_system.models.question import Question
from survey_system.services.other_services import QuestionSorter, QuestionCreator
from shared.api_helpers.server_helpers.jwt_and_schema_verification import verify
from survey_system.services.question_getter_service import QuestionChoiceGetterService, QuestionGetterService
from slugify import slugify
from shared.logger.loggers import Error


class SurveysApi(Resource):
    @verify(permissions=['ViewForms'])
    @orm.db_session
    def get(self):
        data = []
        for version in FormVersion.select().order_by(lambda s: (s.form.name, s.version)):
            data.append({'id': version.id, 'name': version.form.name, 'version': version.version})
        return data


class QuestionsApi(Resource):
    @verify(permissions=['ViewForms'])
    @orm.db_session
    def get(self):

        data = []
        filter = request.args.get('filter', 'custom')
        if filter == 'all':
            questions_objects = QuestionService.get_all_questions()
        elif filter == 'predefined':
            questions_objects = QuestionService.get_system_questions()
        else:
            questions_objects = QuestionService.get_non_system_questions()

        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        pages = math.ceil(len(questions_objects) / per_page)
        sort_param, sort_order = request.args.get('sort', 'id:asc').split(':')

        questions = QuestionSorter.sort_by(questions_objects, sort_param, sort_order)

        for question in questions.page(page, per_page):
            question_dict = question.to_dict()
            question_dict['type_description'] = QuestionType.to_human(question.type)
            question_dict['predefined'] = 'Yes' if question.is_system() else 'No'

            data.append(question_dict)

        pagination = {
            'page': page,
            'per_page': per_page,
            'pages': pages,
            'sort': f'{sort_param}:{sort_order}'
        }

        response = {
            'questions': data,
            'pagination': pagination
        }

        return response

    @orm.db_session
    def post(self):
        QuestionCreator.validate(request.json)
        question = QuestionCreator.create(request.json)
        orm.flush()
        return question.to_dict(), 201

class QuestionApi(Resource):
    @verify(permissions=['ViewForms'])
    @orm.db_session
    def delete(self, question_id):

        question = QuestionGetterService.get_from_user_and_id(get_current_api_user(), question_id, strict=True, main_resource=True)

        if orm.count(question.orderInSurvey) > 0:
            return 'You can not delete this question because it is linked to a survey.', 400

        question.delete()

        return '', 204

    @verify(permissions=['ViewForms'])
    @orm.db_session
    def get(self, question_id):
        language = request.args.get('language', 1)

        question = QuestionGetterService.get_from_user_and_id(get_current_api_user(), question_id, strict=True, main_resource=True)

        question_dict = question.to_dict()
        if question_dict['minValue'] is None:
            question_dict['minValue'] = ''
        if question_dict['maxValue'] is None:
            question_dict['maxValue'] = ''
        question_dict['full_question'] = question.getText(language)
        question_dict['variableName'] = question.getVariableName(language)
        question_dict['typeDescription'] = QuestionType.to_human(question.type)
        question_dict['language'] = language
        choices = []

        for choice in question.getChoices():
            if question.is_numeric_type():
                choices.append({'order': choice.order, 'value': choice.value_numeric})
            else:
                choices.append({'order': choice.order, 'value': choice.getText(language)})

        question_dict['choices'] = choices

        return question_dict, 200

    @verify(permissions=['ViewForms'])
    @orm.db_session
    def put(self, question_id):

        question = QuestionGetterService.get_from_user_and_id(get_current_api_user(), question_id, strict=True, main_resource=True)
        data = request.json
        data['type'] = question.type
        QuestionCreator.validate(data)
        if 'icon' in data:
            question.icon = data['icon'] or ''
        if 'name' in data:
            question.name = data['name']
            question.slug = slugify(data['name'])
            question.setVariableName(data['name'], 1)
        if 'full_question' in data:
            question.setText(data['full_question'], 1)
        if 'minValue' in data:
            question.minValue = data['minValue'] or None
        if 'maxValue' in data:
            question.maxValue = data['maxValue'] or None
        if 'unit' in data:
            question.unit = data['unit']
        if 'regex' in data:
            if not QuestionCreator.is_valid_regex(data.get("regex")):
                raise Error("Invalid RegExp")
            question.additional_data = question.additional_data | {"regex": data.get("regex")}

         # Update additional_data fields
        additional_data = question.additional_data or {}

        # Handle 'regex' if provided in the update data
        if 'regex' in data.get('additional_data', {}):
            if not QuestionCreator.is_valid_regex(data.get("additional_data").get("regex")):
                raise Error("Invalid RegExp")
            additional_data["regex"] = data.get("additional_data").get("regex")

        # Handle 'picture_type' if provided in the update data
        if 'picture_type' in data.get('additional_data', {}):
            additional_data["picture_type"] = data.get('additional_data')["picture_type"]

        # Handle 'picture_instructions' if provided in the update data
        if 'picture_instructions' in data.get('additional_data', {}):
            additional_data["picture_instructions"] = data.get('additional_data')["picture_instructions"]

        # Save updated additional_data back to the question
        question.additional_data = additional_data

        if 'choices' in data and data['choices']:
            for choice_data in data['choices']:
                if choice_data.get('id', None):
                    choice = QuestionChoiceGetterService.get_from_user_and_id(get_current_api_user(), choice_data['id'], strict=True, main_resource=True)
                    choice.order = choice_data['order']
                    if question.type == QuestionType.choice_numeric:
                        choice.value_numeric = choice_data['value']
                    elif question.type == QuestionType.choice_text:
                        choice.text.select().first().value_text = choice_data['value']
                elif question.type == QuestionType.choice_numeric:
                    QuestionCreator.create_choice_numeric_question(question, [choice_data])
                else:
                    QuestionCreator.create_choice_text_question(question, [choice_data], 1)

        for oq in question.orderInSurvey:
            oq.survey.update_cached_data()


    @verify(permissions=['ViewForms'])
    @orm.db_session
    def post(self, question_id):
        params = request.json

        name = params.get('name')
        version = Question.last_version_by_name(name) + 1
        params['version'] = version

        errors = QuestionCreator.validate(params)

        if len(errors) == 0:
            question = QuestionCreator.create(params, version=version)
            return question.to_dict(), 201
        else:
            return errors, 422


class QuestionTypesApi(Resource):
    @verify(permissions=['ViewForms'])
    @orm.db_session
    def get(self):
        l = [t for t in QuestionType.to_list() if t != QuestionType.group]
        return [{'id': t, 'name': QuestionType.to_human(t)} for t in sorted(l, key=QuestionType.to_human)]
