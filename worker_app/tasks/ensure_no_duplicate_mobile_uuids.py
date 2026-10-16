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
from after_sales_system.interaction_system.model.interaction_report_model import InteractionTopic, InteractionReport, DiscussedTopic
from survey_system.models.forms import FormVersion
from after_sales_system.planning_system.model.interaction_planning_model import InteractionPlan
from survey_system.models.survey_answer import SurveyAnswer
from payg_loan_system.offers.models import Offer
from payg_loan_system.contracts.models.contract_model import Contract
from payg_loan_system.devices.model.device import Device
from payg_loan_system.devices.model.offline_token_model import OfflineToken
from payg_loan_system.contracts.models.addons_model import ContractAddOn, AddOnOffer


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
    OfflineToken,
    ContractAddOn,
    AddOnOffer
]

@worker_app.task
@orm.db_session
def ensure_no_duplicate_mobile_uuids():
    print('Ensuring there are no duplicate mobile uuids')
    for model in ALL_SYNC_MODELS:
        ensure_no_duplicates_for_model(model)
    
def ensure_no_duplicates_for_model(model):
    entities_all = get_entities_to_migrate(model)
    for entity in entities_all:
        try:
            change_mobile_uuid_of_old_duplicates(model, entity.mobile_uuid)
        except Exception as e:
                print("Exception while changing mobile uuid: "+str(e))
    orm.commit()

def change_mobile_uuid_of_old_duplicates(model, mobile_uuid):
    duplicates = get_entities_with_mobile_uuid(model, mobile_uuid)
    if(len(duplicates)>1):
        print(str(len(duplicates)) + " Duplicates found for mobile uuid: "+str(mobile_uuid))
        max_date = max(e.modifiedDate for e in duplicates)
        to_change = duplicates.filter(lambda d: d.modifiedDate < max_date)
        for d in to_change:
            d.mobile_uuid = generate_uuid()

def get_entities_to_migrate(model):
    return orm.select(m for m in model)

def get_entities_with_mobile_uuid(model, mobile_uuid):
    return orm.select(m for m in model if m.mobile_uuid == mobile_uuid)
