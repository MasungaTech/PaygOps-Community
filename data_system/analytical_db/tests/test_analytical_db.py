from data_system.analytical_db.analytical_db import analytical_db
from datetime import datetime
from pony.orm import db_session, commit
from pony.orm.core import Query
from data_system.analytical_db.services.update_service import AnalyticalDBUpdateService
from data_system.analytical_db.models.question_answers import Question_Answers
from data_system.analytical_db.analytical_db import analytical_db
from survey_system.services.survey_answer_service import SurveyAnswerService
from survey_system.models.forms import FormVersion
from sales_system.leads.models.lead import Lead
from core_system.users.models.user_model import User
from core_system.core_entities import db
from shared.helpers.client_creator import ClientCreator
from shared.database_mapper import DatabaseMapper

DatabaseMapper.generate_map(include_analytical=True)

class RequiredPropertyChecker:

    _model = None
    _EXCEPTIONS = { # relations that are optional for historical reasons but are requried de-facto
        'Client': ['contracts'],
        'Person': ['village'],
        'StockItem': ['device'],
        'StockMovement': ['previous'],
        'Village': ['parent'],
        'HierarchicalOperationalEntity': ['parent']
    }

    def __init__(self, model):
        self._model = model

    def __getattr__(self, item):
        value = getattr(self._model, item)
        if isinstance(value, property):
            return value.fget(self)
        if value.is_required or item in self._EXCEPTIONS.get(self._model.__name__, []):
            if value.py_type == datetime: 
                return datetime.now()
            elif value.is_relation:
                fk_entity = db.entities[value.fk_name] if value.fk_name else value.py_type
                if value.is_collection:
                    return [RequiredPropertyChecker(fk_entity)]
                return RequiredPropertyChecker(fk_entity)
        raise Exception(
            f'Property {item} of model {self._model.__name__} is not required and '+
            'cannot be used in extended_modified_date. Consider using after_update hook'+
            f' in {item} so modifiedDate of {self._model.__name__} is updated.'
        )


class TestAnalyticalDB:

    def test_analytical_db_models_as_expected(self):
        for model in AnalyticalDBUpdateService.MODELS:
            assert issubclass(model, analytical_db.Entity)
            assert issubclass(model.base_model, db.Entity)
            assert isinstance(model.base_model.select(), Query)
            query = model.selector(model.base_model.select())
            monad = query._translator.expr_monads[0]
            if hasattr(monad, 'attr') and monad.attr != model.base_model._pk_:
                raise Exception('The first item returned by '+model.__name__+'.selector must be '+str(model.base_model._pk_))
            print(f'Checking {model.__name__}')
            model.extended_modified_date(RequiredPropertyChecker(model.base_model))

    def test_questions_answers_syncing(self, capsys):
        commit()
        AnalyticalDBUpdateService.update()
        with db_session:
            assert AnalyticalDBUpdateService._get_all_analytical_db_ids(Question_Answers).count() == 0
        with db_session:
            data = {
                'form_id': FormVersion.select(lambda s: s.form.name == 'Phone Charging Review').first().id,
                'subject_lead_id': Lead.select().first().id,
                'answers': {
                    'q1': '1',
                    'q2': '1',
                }
            }
            SurveyAnswerService._add_from_data_and_user_core(data, User.get(username="super_admin@test.com"))
        AnalyticalDBUpdateService.update()
        with db_session:
            assert AnalyticalDBUpdateService._get_all_analytical_db_ids(Question_Answers).count() == 2

    def test_questions_answers_update_when_registering(self, capsys, good_api_key, api_client):
        before_update_time = datetime.now()
        with db_session:
            lead = ClientCreator.create_lead()
            commit()
            user = User.get(username="super_admin@test.com")
            data = {
                'form_id': FormVersion.select(lambda s: s.form.name == 'Phone Charging Review').first().id,
                'subject_lead_id': lead.id,
                'answers': {
                    'q1': '2',
                    'q2': '2',
                }
            }
            SurveyAnswerService._add_from_data_and_user_core(data, user)
            old_offer_id = lead.offer.id
        AnalyticalDBUpdateService.update()
        with db_session:
            self._check_changes(Question_Answers, {
                'answered_by_lead_id': lead.id,
                'answered_by_client_id': None
            }, before_update_time, 2)
            lead = db.Lead.get(id=lead.id)
            lead.offer = db.Offer.get(id=old_offer_id)
        AnalyticalDBUpdateService.update()
        with db_session:
            client = ClientCreator.register_lead(api_client, good_api_key, Lead.get(id=lead.id))
        AnalyticalDBUpdateService.update()
        self._check_changes(Question_Answers, {
            'answered_by_lead_id': lead.id,
            'answered_by_client_id': client.id
        }, before_update_time, 2)
        AnalyticalDBUpdateService.update()
        with db_session:
            assert AnalyticalDBUpdateService._get_all_analytical_db_ids(Question_Answers).count() == 4

        before_update_time = datetime.now()
        with db_session:
            lead = Lead.get(id=lead.id)
            user = User.get(username="super_admin@test.com")
            data = {
                'form_id': FormVersion.select(lambda s: s.form.name == 'Phone Charging Review').first().id,
                'subject_lead_id': lead.id,
                'answers': {
                    'q1': '3',
                    'q2': '3',
                }
            }
            SurveyAnswerService._add_from_data_and_user_core(data, user)

        self._check_changes(Question_Answers, {
            'is_last_answer': lambda d: d['date'] > before_update_time,
        }, before_update_time, 4)
        AnalyticalDBUpdateService.update(only_models=[Question_Answers])
        with db_session:
            assert AnalyticalDBUpdateService._get_all_analytical_db_ids(Question_Answers).count() == 6

    @staticmethod
    @db_session
    def _check_changes(model, changes, since, changed_count):
        changed_objs = model.base_model.select(lambda o: o.modifiedDate >= since)
        assert changed_count == changed_objs.count()
        changed_selected = model.selector(changed_objs)
        for changed in changed_selected:
            data = model.converter(changed)
            for change in changes:
                op_db_val = changes[change](data) if callable(changes[change]) else changes[change]
                an_db_val = data[change]
                if isinstance(data[change], analytical_db.Entity):
                    an_db_val = data[change].id
                if op_db_val != an_db_val:
                    raise Exception('Failed to check changes: '+str(op_db_val)+' was expected instead of '+str(an_db_val)+' in "'+change+'"', data)
    
    # @db_session
    # def test_analytical_db_performance(self):
    #     lead_id = None
    #     sys.stdout = open(os.devnull, 'w')
    #     for _ in range(1000):
    #         lead = ClientCreator.create_lead()
    #         if not lead_id: 
    #             flush()
    #             lead_id = lead.id
    #     sys.stdout = sys.__stdout__
    #     AnalyticalDBUpdateService.update(only_models=[Leads])
    #     db.execute(f'UPDATE lead SET modifieddate = strftime(\'%Y-%m-%d %H:%M:%f\',\'now\') WHERE id >= {lead_id}')
    #     t0 = time.time()
    #     AnalyticalDBUpdateService.update(only_models=[Leads])
    #     print('Update lasted '+ "%.2fs" % (time.time()-t0))
    #     raise Exception

