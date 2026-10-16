from pony import orm
from worker_app.worker_app import worker_app
from payg_loan_system.devices.model.device import Device
from shared.api_helpers.client_helpers.uuid_generation_helpers import generate_uuid
from sales_system.lead_generator.model import LeadGenerator
from sales_system.leads.models.lead_status import LeadStatus
from sales_system.leads.models.lead import Lead
from payg_loan_system.transaction_requests.models import TransactionRequest
from core_system.client.models import Client
from core_system.operational_entities.models import Village
from survey_system.models.forms import FormVersion
from survey_system.models.survey_answer import SurveyAnswer
from payg_loan_system.offers.models import Offer
from payg_loan_system.contracts.models.contract_model import Contract
from payg_loan_system.devices.model.offline_token_model import OfflineToken
import config

if config.ENABLE_ENTERPRISE_FEATURES:
    from after_sales_system.interaction_system.model.interaction_report_model import InteractionTopic, InteractionReport, DiscussedTopic
    from after_sales_system.planning_system.model.interaction_planning_model import InteractionPlan
else:
    InteractionTopic = InteractionReport = DiscussedTopic = InteractionPlan = None


ALL_SYNC_MODELS = [
    LeadGenerator,
    Lead,
    TransactionRequest,
    Client,
    Village,
    InteractionTopic,
    FormVersion,
    InteractionReport,
    InteractionPlan,
    SurveyAnswer,
    DiscussedTopic,
    Offer,
    Contract,
    Device,
    LeadStatus,
    OfflineToken
]

ALL_SYNC_MODELS = [model for model in ALL_SYNC_MODELS if model is not None]

@worker_app.task
@orm.db_session
def migrate_mobile_uuids():
    print('Migrating mobile uuids')
    for model in ALL_SYNC_MODELS:
        migrate_mobile_uuids_for_model(model)
    
def migrate_mobile_uuids_for_model(model):
    page_items = 1000
    entities_all = get_entities_to_migrate(model)
    count = entities_all.count()
    print(str(count)+' mobile uuids to populate for table '+str(model._table_))
    while count != 0:
        entities = entities_all.page(1, page_items)
        for entity in entities:
            entity.mobile_uuid = generate_uuid()
        orm.commit()
        entities_all = get_entities_to_migrate(model)
        count = entities_all.count()
        print(str(count) + ' mobile uuids left to populate for table '+str(model._table_))

def get_entities_to_migrate(model):
    return orm.select(m for m in model if m.mobile_uuid is None)
