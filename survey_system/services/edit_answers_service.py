from pony.orm.core import rollback
from shared.api_helpers.hook_helpers.process_hook import add_hook_after_commit
from survey_system.models.answer import Answer
from survey_system.models.question_type import QuestionType
from survey_system.models.answer_group import AnswerGroup
from pony import orm
from shared.logger.loggers import Error
from sales_system.leads.services.lead_status_change_service import LeadStatusChangeService
from core_system.core_entities import db
from survey_system.services.survey_answer_data_service import SurveyAnswerDataService
from survey_system.services.individual_answer_service import AnswerService
from datetime import datetime, date


class EditSurveyAnswerAnswersService:

    @classmethod
    def edit_survey_answer_answers(cls, survey_answer, answer_dict, use_names=False, update_status=False, skip_hook=False, user=None):
        skip_questions = []
        protected_responses = []
        if not user.can_access('AnswerProtectedQuestionForms', person=survey_answer.person_answering):
            # We keep track of the answer to protected questions, to allow them again
            skip_questions = orm.select(q.question.id for q in survey_answer.surveyAnswered.questions if q.protected)[:]
            protected_responses = [a.getValue() for a in survey_answer.answers if a.question.id in skip_questions]
        cls._clear_existing_answers(survey_answer)
        cls._handle_survey_answer_change(survey_answer, answer_dict, use_names=use_names, update_status=update_status, skip_hook=skip_hook, user=user, protected_responses=protected_responses)
        return survey_answer

    @classmethod
    def add_survey_answer_answers(cls, survey_answer, answer_dict, use_names=False, update_status=False, skip_hook=False, user=None):
        cls._handle_survey_answer_change(survey_answer, answer_dict, use_names=use_names, update_status=update_status, skip_hook=skip_hook, user=user)
        return survey_answer

    @classmethod
    def _handle_survey_answer_change(cls, survey_answer, answer_dict, use_names=False, update_status=False, skip_hook=False, user=None, protected_responses=None):
        cls._put_answers_in_survey_answer(survey_answer, answer_dict, use_names=use_names, user=user, protected_responses=protected_responses)
        if survey_answer.lead_answering and not survey_answer.client_answering:
            if update_status:
                LeadStatusChangeService.update(survey_answer.lead_answering)
            if not skip_hook:
                add_hook_after_commit(db, 'lead_edited', survey_answer.lead_answering.get_serialized_object())
        elif survey_answer.client_answering:
            if not skip_hook:
                add_hook_after_commit(db, 'client_edited', survey_answer.client_answering.get_serialized_object())
        if not skip_hook:
            survey_answer_data = SurveyAnswerDataService.get_survey_answer_data_dict(survey_answer, use_names=True)
            add_hook_after_commit(db, 'custom_form_answered', survey_answer_data)
            if SurveyAnswerDataService.check_if_all_picture_sign_uploaded(survey_answer):
                add_hook_after_commit(db, 'custom_form_answered_uploaded', survey_answer_data)

    @classmethod
    def _put_answers_in_survey_answer(cls, survey_answer, answer_dict, questions=None, group=None, use_names=False, user=None, protected_responses=None):
        if not questions:
            questions = survey_answer.getQuestionsInOrder()

        for question in questions:
            cls._store_all_answers_for_question(survey_answer, question, answer_dict, group, use_names, user=user, protected_responses=protected_responses)

    @classmethod
    def _store_all_answers_for_question(cls, survey_answer, question, answer_dict, group, use_names, user=None, protected_responses=None):
        all_answers = cls._get_answers_to_question(question, answer_dict, use_names)
        answer_count = 0
        if question.getType() != QuestionType.group:
            for index, answer in enumerate(all_answers):
                answer_count += cls._store_answer_for_question(survey_answer, question, answer, group, index, use_names, user=user, protected_responses=protected_responses)
        else:
            for index, answer in enumerate(all_answers):
                answer_count += cls._store_answer_for_group_question(survey_answer, question, answer, index, use_names, user=user, protected_responses=protected_responses)
        cls._check_number_of_answers(question, answer_count)

    @classmethod
    def _store_answer_for_question(cls, survey_answer, question, answer, group, index, use_names, user=None, protected_responses=None):
        if cls._is_valid_answer(answer, question, user=user, person=survey_answer.person_answering, protected_responses=protected_responses, use_names=use_names):
            this_answer = Answer(question=question.question,
                                surveyAnswer=survey_answer,
                                orderInSurveyAnswer=index,
                                grouping=group)
            this_answer.set_value(answer, use_names)
            return 1
        return 0

    @classmethod
    def _store_answer_for_group_question(cls, survey_answer, question, answer, index, use_names, user=None, protected_responses=None):
        if cls._is_valid_answer(answer, question, user=user, person=survey_answer.person_answering, protected_responses=protected_responses, use_names=use_names):
            group = AnswerGroup()
            this_answer = Answer(question=question.question,
                                surveyAnswer=survey_answer,
                                orderInSurveyAnswer=index,
                                grouping=group)
            cls._put_answers_in_survey_answer(survey_answer, answer, question.getSubQuestions(), group, use_names=use_names, user=user, protected_responses=protected_responses)
            return 1
        return 0

    @classmethod
    def _check_number_of_answers(cls, question, answer_count):
        max_answers = question.maxAnswers
        if max_answers == 0:  # That would mean unlimited answers
            return

        if answer_count > max_answers:
            raise Error('There should be no more than {max_answers} answer(s) for this question: {question_name} (ID: {question_id})', force_format=True, max_answers=max_answers, question_name=question.question.getText(language=1), question_id=question.id)

        min_answers = question.minAnswers
        if answer_count < min_answers:
            raise Error('There should be at least {min_answers} answer(s) for this question: {question_name} (ID: {question_id})', force_format=True, min_answers=min_answers, question_name=question.question.getText(language=1), question_id=question.id)

    @classmethod
    def _is_valid_answer(cls, answer, question, user=None, person=None, protected_responses=None, use_names=None):
        if answer is not None and answer != '' and answer != [] and answer != {} and answer != [{}]:
            if question.protected and question.question.type != QuestionType.group and not user.can_access('AnswerProtectedQuestionForms', person=person):
                normalized_answer = AnswerService.normalize_value(question, answer, use_names)
                if protected_responses \
                    and cls._normalized_answer_in_protected_responses(normalized_answer, protected_responses):
                    ...
                else:
                    raise Error('You do not have the permission to answer the question: {question_name}', force_format=True, question_name=question.question.getText(language=1))
            return True
        return False

    @classmethod
    def _has_multiple_answers(cls, answers):
        return isinstance(answers, list)

    @classmethod
    def _get_answers_to_question(cls, question, answer_dict, use_names):
        if isinstance(answer_dict, list):
            answers = [a.get('answers') for a in answer_dict if a.get('question_name') in [question.question.name, question.question.slug]]
            if answers:
                if isinstance(answers[0], list):
                    answers = answers[0]
        elif not use_names:
            answers = cls._get_answers_to_question_by_id(answer_dict, question.id)
        else:
            answers = answer_dict.get(question.question.name, answer_dict.get(question.question.slug))
        if not cls._has_multiple_answers(answers) or question.question.type == QuestionType.gps_surface and not isinstance(answers[0], list):
            answers = [answers]
        return answers

    @classmethod
    def _get_answers_to_question_by_id(cls, answer_dict, question_id):
        question_id = str(question_id)
        if question_id in answer_dict:
            return answer_dict[question_id]
        else:
            return answer_dict.get(f'q{question_id}')

    @classmethod
    def _clear_existing_answers(cls, survey_answer, skip_questions=[]):
        orm.delete(A for A in Answer if A.surveyAnswer == survey_answer and A.question.id not in skip_questions)

    @classmethod
    def _normalized_answer_in_protected_responses(cls, normalized_answer, protected_responses):
        if normalized_answer in protected_responses:
            return True
        
        # We only compare the actual date without the seconds in that case
        if isinstance(normalized_answer, datetime):
            normalized_date = normalized_answer.date()
            for pr in protected_responses:
                if isinstance(pr, datetime) and pr.date() == normalized_date:
                    return True
                if isinstance(pr, date) and pr == normalized_date:
                    return True

        if isinstance(normalized_answer, str) and '\n' in normalized_answer:
            protected_responses = str(protected_responses).replace('\n', '').replace(' ', '').strip()
            normalized_answers_list = normalized_answer.split('\n')
            
            for n_ans in normalized_answers_list:
                n_ans = n_ans.replace('\n', '').replace(' ', '').strip()
                if n_ans not in str(protected_responses):
                    return False
            return True

