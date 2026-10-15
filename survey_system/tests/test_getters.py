import pytest


from survey_system.methods.getter_methods import getSurveyFromID
from survey_system.methods.getter_methods import getQuestionInSurvey
from survey_system.methods.getter_methods import getQuestionChoiceFromQuestion
from survey_system.methods.getter_methods import getQuestionChoiceFromId


class TestGetterMethods:

    def test_get_survey_from_id(self):
        some_survey_id = 0

        result = getSurveyFromID(some_survey_id)

        assert result is None

    @pytest.mark.skip(reason="No easy way of create questionary and question name objects")
    def test_get_question_in_survey(self):
        result = getQuestionInSurvey('some_questionary', 'some_question_name')

        assert result is None

    @pytest.mark.skip(reason="No easy way of create question and question name objects")
    def test_get_question_choice_from_question(self):
        result = getQuestionChoiceFromQuestion('some_question', 'some_name')

        assert result is None

    def test_get_question_choice_from_id(self):

        result = getQuestionChoiceFromId(0)

        assert result is None
