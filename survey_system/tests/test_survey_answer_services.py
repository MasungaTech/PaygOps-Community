from datetime import date, datetime

import pytest
from mock import MagicMock, patch

from survey_system.services.edit_answers_service import EditSurveyAnswerAnswersService
from survey_system.services.individual_answer_service import AnswerService


def _ordered_question(name, slug=None, question_id=1, ordered_id=None):
    question = MagicMock()
    question.id = ordered_id if ordered_id is not None else question_id
    question.question = MagicMock()
    question.question.name = name
    question.question.slug = slug or name.lower().replace(' ', '-')
    question.question.id = question_id
    return question


class TestSurveyInterfaces:
    survey_dict = {
        'q113': 'when this client called me he reported he meed to be uninstallation because of battery  problem and he plan to buy another system and for now is not at home and he is at Zanzibar and his wife is at home so i told him i will reported to the hub concerned',
        'q114': 'reported to the hub concerned in order to be uninstall on time 2',
        '112': 'uninstallation'
    }

    def test_get_answer_for_ordered_question_in_empty_dict_returns_none(self):
        answer = EditSurveyAnswerAnswersService._get_answers_to_question_by_id({}, '113')
        assert answer is None

    def test_get_answer_for_ordered_question_in_dict_returns_none(self):
        answer = EditSurveyAnswerAnswersService._get_answers_to_question_by_id(self.survey_dict, '138')
        assert answer is None

    def test_get_answer_for_ordered_question_in_dict_returns_uninstallation(self):
        answer = EditSurveyAnswerAnswersService._get_answers_to_question_by_id(self.survey_dict, '112')
        assert answer == 'uninstallation'

    def test_get_answer_for_ordered_question_in_dict_returns_reported_answer(self):
        expected_answer = 'reported to the hub concerned in order to be uninstall on time 2'

        answer_114 = EditSurveyAnswerAnswersService._get_answers_to_question_by_id(self.survey_dict, '114')
        answer_q114 = EditSurveyAnswerAnswersService._get_answers_to_question_by_id(self.survey_dict, 'q114')

        assert expected_answer == answer_114
        assert expected_answer == answer_q114


class TestMergeWithExistingAnswers:
    """Regression: partial edits must keep omitted answers (e.g. required question groups)."""

    def test_answer_dict_contains_question_by_name_in_list_format(self):
        question = _ordered_question('Instructions', 'instructions')
        answer_dict = [
            {'question_name': 'Instructions', 'answers': 'Updated text'},
        ]
        assert EditSurveyAnswerAnswersService._answer_dict_contains_question(
            question, answer_dict, use_names=True
        )

    def test_answer_dict_does_not_contain_omitted_question(self):
        question = _ordered_question('Questions Group', 'questions-group')
        answer_dict = [
            {'question_name': 'Instructions', 'answers': 'Updated text'},
        ]
        assert not EditSurveyAnswerAnswersService._answer_dict_contains_question(
            question, answer_dict, use_names=True
        )

    def test_answer_dict_contains_question_by_slug_in_list_format(self):
        question = _ordered_question('Questions Group', 'questions-group')
        answer_dict = [
            {'question_name': 'questions-group', 'answers': []},
        ]
        assert EditSurveyAnswerAnswersService._answer_dict_contains_question(
            question, answer_dict, use_names=True
        )

    @patch(
        'survey_system.services.edit_answers_service.SurveyAnswerAnswersGetterService'
        '.get_answers_with_questions'
    )
    def test_partial_list_edit_keeps_existing_question_group(self, get_answers):
        instructions = _ordered_question('Instructions', 'instructions', question_id=1, ordered_id=10)
        questions_group = _ordered_question(
            'Questions Group', 'questions-group', question_id=2, ordered_id=20
        )
        survey_answer = MagicMock()
        survey_answer.getQuestionsInOrder.return_value = [instructions, questions_group]

        group_answers = [[
            {'question_name': 'Contract reference', 'answers': 'C475590014'},
            {'question_name': 'Contract outstanding balance', 'answers': 1074.58},
        ]]
        get_answers.return_value = [
            {'question_name': 'Instructions', 'answers': 'Original instructions'},
            {'question_name': 'Questions Group', 'answers': group_answers},
        ]

        partial_update = [
            {
                'question_name': 'Instructions',
                'answers': 'Some of the answers are empty, please fill out all fields.',
            }
        ]

        merged = EditSurveyAnswerAnswersService._merge_with_existing_answers(
            survey_answer, partial_update, use_names=True
        )

        assert len(merged) == 2
        by_name = {item['question_name']: item['answers'] for item in merged}
        assert by_name['Instructions'] == (
            'Some of the answers are empty, please fill out all fields.'
        )
        assert by_name['Questions Group'] == group_answers

    @patch(
        'survey_system.services.edit_answers_service.SurveyAnswerAnswersGetterService'
        '.get_answers_with_questions'
    )
    def test_partial_dict_edit_keeps_existing_answers(self, get_answers):
        instructions = _ordered_question('Instructions', 'instructions', question_id=1, ordered_id=10)
        questions_group = _ordered_question(
            'Questions Group', 'questions-group', question_id=2, ordered_id=20
        )
        survey_answer = MagicMock()
        survey_answer.getQuestionsInOrder.return_value = [instructions, questions_group]

        get_answers.return_value = {
            'Instructions': ['Original instructions'],
            'Questions Group': [[{'Contract reference': 'C475590014'}]],
        }

        merged = EditSurveyAnswerAnswersService._merge_with_existing_answers(
            survey_answer,
            {'Instructions': ['Updated instructions']},
            use_names=True,
        )

        assert merged['Instructions'] == ['Updated instructions']
        assert merged['Questions Group'] == [[{'Contract reference': 'C475590014'}]]

    @patch(
        'survey_system.services.edit_answers_service.SurveyAnswerAnswersGetterService'
        '.get_answers_with_questions'
    )
    def test_provided_answer_overrides_existing(self, get_answers):
        group = _ordered_question('Questions Group', 'questions-group', question_id=2, ordered_id=20)
        survey_answer = MagicMock()
        survey_answer.getQuestionsInOrder.return_value = [group]

        get_answers.return_value = [
            {'question_name': 'Questions Group', 'answers': [[{'question_name': 'A', 'answers': 'old'}]]},
        ]
        update = [
            {'question_name': 'Questions Group', 'answers': [[{'question_name': 'A', 'answers': 'new'}]]},
        ]

        merged = EditSurveyAnswerAnswersService._merge_with_existing_answers(
            survey_answer, update, use_names=True
        )

        assert len(merged) == 1
        assert merged[0]['answers'] == [[{'question_name': 'A', 'answers': 'new'}]]


class TestSetDatetimeQuestion:
    """Merged existing answers are passed back as datetime objects, not strings."""

    @pytest.mark.parametrize('value, expected', [
        ('2022-03-13T22:40:09.613478Z', datetime(2022, 3, 13, 22, 40, 9, 613478)),
        (datetime(2022, 3, 13, 22, 40, 9), datetime(2022, 3, 13, 22, 40, 9)),
        (date(2022, 3, 13), datetime(2022, 3, 13)),
    ])
    @patch('shared.helpers.clock.SettingsService.get_setting', return_value='UTC')
    def test_accepts_strings_and_datetime_objects(self, _get_setting, value, expected):
        answer = MagicMock()
        AnswerService._set_datetime_question(answer, value)
        assert answer.value_date == expected
