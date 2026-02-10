from core_system.person.models.person_model import Person
from pony import orm
from shared.logger.loggers import Error
from shared.services.settings_service import SettingsService
from survey_system.models.survey_answer import SurveyAnswer


class ClientMergerService:

    @classmethod
    def merge(cls, original_client, selected_client):
        if not (original_client and selected_client):
            raise Error('You need to provide both the original and the target client', code="CLIENTS_MUST_EXISTS")
        if original_client == selected_client:
            raise Error('You cannot merge the same client', code='CLIENTS_MUST_BE_DIFFERENT')
        if not SettingsService.get_setting('AllowMultipleContracts') and not original_client.eligible_for_new_contract and not selected_client.eligible_for_new_contract:
            raise Error('Both Clients have active contracts or leads and multiple active contracts is not enabled', code="MULTIPLE_CONTRACTS_NOT_ENABLED")
        for contract in selected_client.contracts:
            contract.client = original_client

        for lead in selected_client.person.lead:
            lead.person = original_client.person

        selected_client_numbers = selected_client.person.phoneNumbers
        
        for number in selected_client_numbers:
            if number not in original_client.person.phoneNumbers:
                original_client.person.phoneNumbers.add(number)

        for answer in selected_client.person.surveyAnswered:
            answer.client_answering = original_client
            answer.personAnswering = original_client.person

        cls._fix_survey_answers_coherence(original_client=original_client)
        

        original_client.payment_wallets += selected_client.payment_wallets
        original_client.ActivationRequests += selected_client.ActivationRequests
        original_client.MentorRequests += selected_client.MentorRequests
        original_client.tags += selected_client.tags
        original_client.Assets += ' ' + selected_client.Assets
        original_client.interactionReports += selected_client.interactionReports
        original_client.interactionPlans += selected_client.interactionPlans
        original_client.issues += selected_client.issues
        original_client.transaction_requests += selected_client.transaction_requests
        original_client.destined_stock += selected_client.destined_stock
        original_client.wallets_owned_history += selected_client.wallets_owned_history
        original_client.forms_answered += selected_client.forms_answered
        cls._migrate_person(original_client, selected_client)
        original_client.before_update()


    @classmethod
    def _migrate_person(cls, original_client, selected_client):
        
        if selected_client.person.user:
            raise Error('The selected client cannot be merged because it has an associated user')
        
        if selected_client.person.leadGenerator:
            raise Error('The selected client cannot be merged because it has an associated lead generator')

        original_client.person.cached_reconciled_payments += selected_client.person.cached_reconciled_payments
        original_client.person.reconciled_payments += selected_client.person.reconciled_payments
        original_client.person.cached_addons += selected_client.person.cached_addons
        original_client.person.lead += selected_client.person.lead
        original_client.person.surveyAnswered += selected_client.person.surveyAnswered
        original_client.person.surveyGiven += selected_client.person.surveyGiven
        person = selected_client.person
        selected_client.delete()
        person.delete()


    @classmethod
    def _fix_survey_answers_coherence(cls, original_client):
        for answer in original_client.person.surveyAnswered:
             answer.check_first_last_coherence()