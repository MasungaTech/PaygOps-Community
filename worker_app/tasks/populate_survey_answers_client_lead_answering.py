from survey_system.models.survey_answer import SurveyAnswer
from pony import orm
from worker_app.worker_app import worker_app


@worker_app.task
@orm.db_session(sql_debug=False)
def populate_survey_answers_client_lead_answering():
    surveys = get_surveys()
    print(f'Populating client and lead answering info for survey answers')
    while surveys:
        i = 0
        for survey in surveys:
            i += 1
            if survey.personAnswering.client and (not survey.started or survey.personAnswering.client.RegistrationDate <= survey.started):
                survey.client_answering = survey.personAnswering.client
            else:
                survey.lead_answering = survey.personAnswering.lead.select().first()
        print(f'{i} answers populated')
        orm.commit()
        surveys = get_surveys()

def get_surveys():
    return SurveyAnswer.select(lambda sw: not sw.lead_answering and not sw.client_answering).limit(1000)