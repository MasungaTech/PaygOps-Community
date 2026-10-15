import json
import uuid

from mock import patch
from pony.orm import db_session

from core_system.users.models.user_model import User
from payg_loan_system.transaction_requests.services.cancellation_service import (
    CancelContractTransactionService,
)
from sales_system.leads.models.lead import Lead
from shared.helpers.client_creator import ClientCreator


class TestCancelTransactionDuplicateLead:

    @db_session
    def test_cancel_with_duplicate_lead_false_string_creates_no_lead(
        self, api_client, good_api_key
    ):
        client = ClientCreator.create(api_client, good_api_key)
        user = User.get(username="super_admin@test.com")
        contract = client.contracts.select().first()
        leads_before = Lead.select().count()

        request = CancelContractTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            duplicate_lead="False",
            send_sms="False",
            note="Cancelled as test",
        )

        answers = json.loads(request.answer_data)
        assert request.success is True
        assert answers[0]['status'] == 'CONTRACT_CANCELLATION_SUCCESS'
        assert Lead.select().count() == leads_before

    @db_session
    def test_cancel_with_duplicate_lead_false_bool_creates_no_lead(
        self, api_client, good_api_key
    ):
        client = ClientCreator.create(api_client, good_api_key)
        user = User.get(username="super_admin@test.com")
        contract = client.contracts.select().first()
        leads_before = Lead.select().count()

        request = CancelContractTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            duplicate_lead=False,
            send_sms=False,
        )

        answers = json.loads(request.answer_data)
        assert request.success is True
        assert answers[0]['status'] == 'CONTRACT_CANCELLATION_SUCCESS'
        assert Lead.select().count() == leads_before

    @db_session
    def test_cancel_with_duplicate_lead_omitted_creates_no_lead(
        self, api_client, good_api_key
    ):
        client = ClientCreator.create(api_client, good_api_key)
        user = User.get(username="super_admin@test.com")
        contract = client.contracts.select().first()
        leads_before = Lead.select().count()

        request = CancelContractTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
        )

        answers = json.loads(request.answer_data)
        assert request.success is True
        assert answers[0]['status'] == 'CONTRACT_CANCELLATION_SUCCESS'
        assert Lead.select().count() == leads_before

    @db_session
    def test_cancel_with_duplicate_lead_true_creates_lead(
        self, api_client, good_api_key
    ):
        client = ClientCreator.create(api_client, good_api_key)
        user = User.get(username="super_admin@test.com")
        contract = client.contracts.select().first()
        leads_before = Lead.select().count()

        request = CancelContractTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            duplicate_lead="True",
        )

        answers = json.loads(request.answer_data)
        assert request.success is True
        assert answers[0]['status'] == 'CONTRACT_AND_LEAD_CANCELLATION_SUCCESS'
        assert 'new_lead' in answers[0]
        assert Lead.select().count() == leads_before + 1

    @db_session
    def test_cancel_duplicate_lead_false_string_does_not_call_add_lead(
        self, api_client, good_api_key
    ):
        client = ClientCreator.create(api_client, good_api_key)
        user = User.get(username="super_admin@test.com")
        contract = client.contracts.select().first()

        with patch('payg_loan_system.actions.deregister.AddLeadService.add_lead') as mock_add_lead:
            request = CancelContractTransactionService.create(
                user=user,
                uuid=str(uuid.uuid1()),
                contract_reference=contract.reference,
                duplicate_lead="False",
            )

        assert request.success is True
        mock_add_lead.assert_not_called()
