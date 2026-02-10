from survey_system.services.edit_answers_service import EditSurveyAnswerAnswersService


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
