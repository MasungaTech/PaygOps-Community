from pony import orm
from survey_system.models.forms import FormVersion
from survey_system.models.question import Question


class TestSurvey:
    def test_in_system_returns_false(self):
        assert FormVersion.in_system('non-existent') is False

    @orm.db_session
    def test_in_system_returns_true(self):
        survey = FormVersion.select().first()

        assert FormVersion.in_system(survey.form.name)


class TestQuestion:
    def test_last_version_by_name_returns_zero(self):
        assert 0 == Question.last_version_by_name('non-existent-reference')
        assert 0 == Question.last_version_by_name(None)

    @orm.db_session
    def test_last_version_by_name_returns_one(self):
        question = Question.select(lambda q: q.version > 0).first()
        assert 1 == Question.last_version_by_name(question.name)
