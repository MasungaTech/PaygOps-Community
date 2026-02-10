import pytest 
from survey_system.form_editor.services import FormService
from pony import orm
from shared.logger.loggers import Error


class TestFormService:

    @orm.db_session
    def test_is_valid_method_when_valid_form_is_given(self):
        form = self._some_form()
        FormService.validate(form)

    @orm.db_session
    def test_is_valid_method_when_empty_dict_is_given(self):
        with pytest.raises(Error):
            FormService.validate({})

    @orm.db_session
    def test_is_valid_method_returns_false_with_negative_orders(self):
        form = self._some_form()

        form.update(
            {
                'questions': [
                    {
                        'order': -1,
                        'question': 1,
                        'min_answers': 0,
                        'max_answers': 1
                    }
                ]
            }
        )

        with pytest.raises(Error):
            FormService.validate(form)

    @orm.db_session
    def test_is_valid_method_returns_false_when_max_answers_is_smaller_than_minimum_answers(self):
        form = self._some_form()

        form.update(
            {
                'questions': [
                    {
                        'order': 1,
                        'question': 1,
                        'min_answers': 2,
                        'max_answers': 1
                    }
                ]
            }
        )

        with pytest.raises(Error):
            FormService.validate(form)

    @orm.db_session
    def test_is_valid_method_returns_false_when_orders_are_repeated(self):
        form = self._some_form()

        form.update(
            {
                'questions': [
                    {
                        'order': 1,
                        'question': 1,
                        'min_answers': 0,
                        'max_answers': 1
                    },
                    {
                        'order': 1,
                        'question': 1,
                        'min_answers': 0,
                        'max_answers': 1
                    }
                ]
            }
        )

        with pytest.raises(Error):
            FormService.validate(form)

    @staticmethod
    def _some_form():
        return {
            'name': 'some_name',
            'icon': 'some_icon',
            'questions': [
                {
                    'order': 1,
                    'max_answers': 1,
                    'min_answers': 0,
                    'question': 1
                }
            ]
        }
