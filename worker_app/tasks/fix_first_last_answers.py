import math

from pony import orm

from shared.logger.loggers import LogService
from survey_system.models.survey_answer import SurveyAnswer
from worker_app.worker_app import worker_app
from shared.logger.loggers import LogAPI


@worker_app.task
def fix_answer_person_first_last():
    check_coherence_f = SurveyAnswer.check_coherence
    SurveyAnswer.check_coherence = lambda s: None # We disable the coherence check while running the fixes
    fix_answer_person()
    fix_answer_first_last()
    SurveyAnswer.check_coherence = check_coherence_f


def fix_answer_first_last():
    from core_system.core_entities import db
    # We get and fix the first answers where there are multiple for one
    with orm.db_session:
        result = db.execute('''
            SELECT s.wrapper, sa.personanswering, COUNT(*) as answer_count 
            FROM surveyanswer sa
            JOIN survey s ON sa.surveyanswered = s.id
            WHERE sa.is_last_answer = true 
            GROUP BY s.wrapper, sa.personanswering 
            HAVING COUNT(*) != 1;
        ''')
        results = [sa for sa in result]
        if len(results) > 0:
            LogAPI.Warning(f'CONSISTENCY ISSUE - Found survey answer with multiple last answers for the same form and person', other_data=results)
        for sa in results:
            SurveyAnswer.check_first_last(sa[0], sa[1])
            orm.commit()
    with orm.db_session:
        result = db.execute('''
            SELECT s.wrapper, sa.personanswering, COUNT(*) as answer_count 
            FROM surveyanswer sa
            JOIN survey s ON sa.surveyanswered = s.id
            WHERE sa.is_first_answer = true 
            GROUP BY s.wrapper, sa.personanswering 
            HAVING COUNT(*) != 1;
        ''')
        results = [sa for sa in result]
        if len(results) > 0:
            LogAPI.Warning(f'CONSISTENCY ISSUE - Found survey answer with multiple first answers for the same form and person', other_data=results)
        for sa in results:
            SurveyAnswer.check_first_last(sa[0], sa[1])
            orm.commit()

    with orm.db_session:
        result = db.execute('''
            SELECT s.wrapper, sa.personanswering, COUNT(*) AS answer_count
			FROM surveyanswer sa
			JOIN survey s ON sa.surveyanswered = s.id
			GROUP BY s.wrapper, sa.personanswering
			HAVING SUM(CASE WHEN sa.is_last_answer = true THEN 1 ELSE 0 END) = 0 and COUNT(*) > 1;
        ''')

        results = [sa for sa in result]
        if len(results) > 0:
            LogAPI.Warning(f'CONSISTENCY ISSUE - Found survey answer with multiple first answers for the same form and person', other_data=results)
        for sa in results:
            SurveyAnswer.check_first_last(sa[0], sa[1])
            orm.commit()

    with orm.db_session:
        result = db.execute('''
            SELECT s.wrapper, sa.personanswering, COUNT(*) AS answer_count
			FROM surveyanswer sa
			JOIN survey s ON sa.surveyanswered = s.id
			GROUP BY s.wrapper, sa.personanswering
			HAVING SUM(CASE WHEN sa.is_first_answer = true THEN 1 ELSE 0 END) = 0 and COUNT(*) > 1;
        ''')

        results = [sa for sa in result]
        if len(results) > 0:
            LogAPI.Warning(f'CONSISTENCY ISSUE - Found survey answer with multiple first answers for the same form and person', other_data=results)
        for sa in results:
            print(list(sa))
            SurveyAnswer.check_first_last(sa[0], sa[1])
            orm.commit()


def fix_answer_person():
    # We check if the client referenced and lead referenced have different persons, we use the lead one if so
    with orm.db_session:
        client_lead_different = list(orm.select(sa.id for sa in SurveyAnswer if sa.lead_answering.person != sa.client_answering.person))
        if len(client_lead_different) > 0:
            LogAPI.Warning(f'CONSISTENCY ISSUE - Found survey answer with different person for client and lead', other_data=client_lead_different)
            for sa in orm.select(sa for sa in SurveyAnswer if sa.id in client_lead_different):
                sa.client_answering = sa.lead_answering.person.client
                sa.personAnswering = sa.lead_answering.person
            orm.commit()
    # We check if the person referenced matches the lead referenced
    with orm.db_session:
        lead_different = list(orm.select(sa.id for sa in SurveyAnswer if sa.lead_answering.person != sa.personAnswering))
        if len(lead_different) > 0:
            LogAPI.Warning(f'CONSISTENCY ISSUE - Found survey answer with different person than in lead', other_data=lead_different)
            for sa in orm.select(sa for sa in SurveyAnswer if sa.id in lead_different):
                sa.personAnswering = sa.lead_answering.person
            orm.commit()
    # We check if the person referenced matches the lead referenced
    with orm.db_session:
        client_different = list(orm.select(sa.id for sa in SurveyAnswer if sa.client_answering.person != sa.personAnswering))
        if len(client_different) > 0:
            LogAPI.Warning(f'CONSISTENCY ISSUE - Found survey answer with different person than in client', other_data=client_different)
            for sa in orm.select(sa for sa in SurveyAnswer if sa.id in client_different):
                sa.personAnswering = sa.lead_answering.person
            orm.commit()


# --- Legacy fixer - Left here to double check if it doesnt find other issue, can be removed later
    
def get_all():
    return orm.select((
            s.id,
            s.client_answering,
            s.lead_answering,
            s.surveyAnswered,
            s.is_first_answer,
            s.is_last_answer
    ) for s in SurveyAnswer)

PAGE_SIZE = 10000

@worker_app.task
def fix_first_answer_old():
    page_size = PAGE_SIZE
    with orm.db_session:
        all_answers = get_all().order_by(lambda a,b,c,d,f,g: a)
        count = all_answers.count()
    number_of_pages = math.ceil(count / page_size)
    for page_n in range(1, number_of_pages + 1):
        try:
            with orm.db_session:
                process_page_first_answer(all_answers, page_n, number_of_pages, page_size)
        except Exception as e:
            with orm.db_session:
                process_page_first_answer(all_answers, page_n, number_of_pages, page_size)


@worker_app.task
def fix_last_answer_old():
    page_size = PAGE_SIZE
    with orm.db_session:
        all_answers = get_all().order_by(lambda a,b,c,d,f,g: orm.desc(a))
        count = all_answers.count()
    number_of_pages = math.ceil(count / page_size)
    for page_n in range(1, number_of_pages + 1):
        try:
            with orm.db_session:
                process_page_no_last_answer(all_answers, page_n, number_of_pages, page_size)
        except Exception as e:
            with orm.db_session:
                process_page_no_last_answer(all_answers, page_n, number_of_pages, page_size)


def process_page_first_answer(all_answers, page_n, number_of_pages, page_size):
    # We do the pages in reverse because the list size reduces with the passes
    print(f'Page {page_n} of {number_of_pages} - {(number_of_pages+1)-page_n}')
    answer_page = all_answers.page((number_of_pages+1)-page_n, page_size)
    for ans in answer_page:
        try:
            process_first_answer(*ans)
        except Exception as e:
            LogService.FatalNoRequest(e)


def process_first_answer(aid, client_answering, lead_answering, survey_answered, is_first_answer, is_last_answer):
    person = client_answering.person if client_answering else None
    if not person:
        person = lead_answering.person if lead_answering else None
    if person:
        answers = SurveyAnswer.select(lambda s: s.surveyAnswered.form == survey_answered.form and s.is_first_answer)
        person_answers = answers.filter(lambda sa: sa.personAnswering == person)
        if not person_answers.exists():
            print(f'Missing a first answer: {aid}')
            is_first_answer = True
            orm.commit()
        elif person_answers.count() > 1:
            print(f'Too many first answers: {aid}')
            if is_first_answer:
                for a in person_answers:
                    if a.id != aid:
                        print(f'Fixed one first issue: {a.personAnswering.id}')
                        a.is_first_answer = False
                        orm.commit()


def process_page_no_last_answer(all_answers, page_n, number_of_pages, page_size):
    # We do the pages in reverse because the list size reduces with the passes
    print(f'Page {page_n} of {number_of_pages} - {(number_of_pages+1)-page_n}')
    answer_page = all_answers.page((number_of_pages+1)-page_n, page_size)
    for ans in answer_page:
        try:
            process_last_answer(*ans)
        except Exception as e:
            LogService.FatalNoRequest(e)


def process_last_answer(aid, client_answering, lead_answering, survey_answered, is_first_answer, is_last_answer):
    person = client_answering.person if client_answering else None
    if not person:
        person = lead_answering.person if lead_answering else None
    if person:
        answers = SurveyAnswer.select(
            lambda s: s.surveyAnswered.form == survey_answered.form and s.is_last_answer
        )
        person_answers = answers.filter(lambda sa: sa.personAnswering == person)
        if not person_answers.exists():
            print(f'Missing a last answer: {aid}')
            SurveyAnswer.get(id=aid).is_last_answer = True
            orm.commit()
        elif person_answers.count() > 1:
            print(f'Too many last answers: {aid}')
            if is_last_answer:
                for a in person_answers:
                    if a.id != aid:
                        print(f'Fixed one last issue: {a.personAnswering.id}')
                        a.is_last_answer = False
                        orm.commit()
