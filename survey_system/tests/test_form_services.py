from shared.logger.loggers import Error
from survey_system.models.question_type import QuestionType
from mock import patch
from pony import orm
import pytest
from survey_system.models.question import Question
from survey_system.services.other_services import QuestionCreator


class TestQuestionCreatorService:
    @patch.object(QuestionCreator, 'create_question')
    def test_question_with_type_0_calls_create_question_function(self, fn):
        QuestionCreator.create({'type': QuestionType.group})

        fn.assert_called_once()

    @patch.object(QuestionCreator, 'create_question')
    def test_question_with_type_1_calls_create_question_function(self, fn):
        QuestionCreator.create({'type': QuestionType.yes_no})

        fn.assert_called_once()

    @patch.object(QuestionCreator, 'create_question')
    def test_question_with_type_2_calls_create_question_function(self, fn):
        QuestionCreator.create({'type': QuestionType.text})

        fn.assert_called_once()

    @patch.object(QuestionCreator, 'create_question')
    def test_question_with_type_3_calls_create_numeric_question_function(self, fn):
        QuestionCreator.create({'type': QuestionType.choice_numeric})

        fn.assert_called_once()

    @patch.object(QuestionCreator, 'create_question')
    def test_create_type_4_calls_create_choice_text_question_function(self, fn):
        QuestionCreator.create({'type': QuestionType.choice_text})

        fn.assert_called_once()

    # @patch.object(QuestionCreator, 'create_choice_numeric_question')
    # def test_question_with_type_5_calls_create_choice_numeric_function(self, fn):
    #     QuestionCreator.create({'type': QuestionType.choice_numeric})

    #     fn.assert_called_once()

    @patch.object(QuestionCreator, 'create_question')
    def test_question_with_type_6_calls_create_question_function(self, fn):
        QuestionCreator.create({'type': QuestionType.picture})

        fn.assert_called_once()

    @patch.object(QuestionCreator, 'create_question')
    def test_create_with_type_7_calls_create_question_function(self, fn):
        QuestionCreator.create({'type': QuestionType.long_text})

        fn.assert_called_once()

    @patch.object(QuestionCreator, 'create_question')
    def test_create_with_type_8_calls_create_question_function(self, fn):
        QuestionCreator.create({'type': QuestionType.checkbox})

        fn.assert_called_once()

    @patch.object(QuestionCreator, 'create_question')
    def test_create_with_type_9_calls_create_date_question_function(self, fn):
        QuestionCreator.create({'type': QuestionType.date})

        fn.assert_called_once()

    def test_create_group_question(self):
        pytest.skip('Missing create group question implementation.')

    @orm.db_session
    def test_create_boolean_question(self):
        expected_question_count = Question.select().count() + 1

        params = self._plain_question_params(
            type=QuestionType.yes_no,
            reference_name='bool_question'
        )

        question = QuestionCreator.create(params)

        assert expected_question_count == Question.select().count()
        assert question.type == QuestionType.yes_no

    @orm.db_session
    def test_create_long_text_question(self):
        expected_question_count = Question.select().count() + 1

        params = self._plain_question_params(
            type=QuestionType.long_text,
            reference_name='long_text_question'
        )

        question = QuestionCreator.create(params)

        assert expected_question_count == Question.select().count()
        assert question.type == QuestionType.long_text

    @orm.db_session
    def test_create_checkbox_question(self):
        expected_question_count = Question.select().count() + 1

        params = self._plain_question_params(
            type=QuestionType.checkbox,
            reference_name='checkbox_question'
        )

        question = QuestionCreator.create(params)

        assert expected_question_count == Question.select().count()
        assert question.type == QuestionType.checkbox

    @orm.db_session
    def test_text_question(self):
        expected_question_count = Question.select().count() + 1
        min_value = 0
        max_value = 50

        params = self._plain_question_params(
            type=QuestionType.text,
            reference_name='text_question',
            min_value=min_value,
            max_value=max_value
        )

        question = QuestionCreator.create(params)

        assert expected_question_count == Question.select().count()
        assert question.type == QuestionType.text
        assert min_value == question.minValue
        assert max_value == question.maxValue

    @orm.db_session
    def test_numeric_question(self):
        expected_question_count = Question.select().count() + 1
        min_value = 0
        max_value = 50
        unit = 'km'

        params = self._plain_question_params(
            type=QuestionType.text,
            reference_name='numeric_question',
            min_value=min_value,
            max_value=max_value,
            unit=unit
        )

        question = QuestionCreator.create(params)

        assert expected_question_count == Question.select().count()
        assert question.type == QuestionType.text
        assert min_value == question.minValue
        assert max_value == question.maxValue
        assert unit == question.unit

    @orm.db_session
    def test_choice_text_question(self):
        expected_question_count = Question.select().count() + 1

        params = self._plain_question_params(
            type=QuestionType.choice_text,
            reference_name='test_choice_text',
        )

        params['choices'] = [
            {'order': 0, 'value': 'C1'},
            {'order': 1, 'value': 'C2'},
            {'order': 2, 'value': 'C3'},
        ]

        question = QuestionCreator.create(params)

        assert expected_question_count == Question.select().count()
        assert question.type == QuestionType.choice_text

        assert 3 == len(question.choices.select())

        expected_texts = ['C1', 'C2', 'C3']
        texts = [qt.getText(params['language']) for qt in question.choices.select()]

        assert expected_texts == sorted(texts)

    @orm.db_session
    def test_choice_numeric_question(self):
        expected_question_count = Question.select().count() + 1

        params = self._plain_question_params(
            type=QuestionType.choice_numeric,
            reference_name='test_choice_numeric',
        )
        print(params)
        params['choices'] = [
            {'order': 0, 'value': 1},
            {'order': 1, 'value': 2},
            {'order': 2, 'value': 3},
        ]

        question = QuestionCreator.create(params)

        assert expected_question_count == Question.select().count()
        assert question.type == QuestionType.choice_numeric

        assert 3 == len(question.choices.select())

        expected_numbers = [1, 2, 3]
        numbers = [qt.value_numeric for qt in question.choices.select()]

        assert expected_numbers == sorted(numbers)

    @orm.db_session
    def test_validate_returns_four_erros(self):
        
        def helper(d):
            with pytest.raises(Error) as error:
                QuestionCreator.validate(d)
            return str(error).lower()

        data = {}
        assert 'name' in helper(data)

        data.update({'name': 'name'})
        assert 'type' in helper(data)

        data.update({'type': QuestionType.numeric})
        assert 'full question' in helper(data)

        data.update({'full_question': 'fullquestion'})
        QuestionCreator.validate(data)

    @orm.db_session
    def test_validate_returns_reference_error(self):
        question = Question.select().first()

        QuestionCreator.validate(
            {
                'name': question.name,
                'full_question': 'Is testing?',
                'type': question.type,
                'version': question.version
            }
        )

    def _plain_question_params(self, type, reference_name, min_value=None, max_value=None, unit=''):
        params = {
            'type': type,
            'name': reference_name,
            'full_question': 'Is this a test question?',
            'minValue': min_value,
            'maxValue': max_value,
            'icon': 'add_location',
            'language': 1,
            'unit': unit
        }

        return params
