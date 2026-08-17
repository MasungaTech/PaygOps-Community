from survey_system.form_editor.question_validator import QuestionValidator
from pony.orm import db_session

class TestQuestionValidator:

    @db_session
    def test_returns_true_when_a_valid_question_is_given(self):
        valid_descriptor = {
            'order': 1,
            'question': 1,
            'min_answers': 0,
            'max_answers': 1
        }
        validator = QuestionValidator(valid_descriptor)
        validator.is_valid()