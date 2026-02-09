import pytest
import uuid
import json
from pony.orm import db_session, rollback
from payg_loan_system.transaction_requests.services.registration_service import \
    RegistrationTransactionService
from core_system.users.models.user_model import User
from shared.helpers.client_creator import ClientCreator
from shared.logger.loggers import Error


class TestRegistrationTransaction:

    @db_session
    def test_registration_transaction(self):

        lead = ClientCreator.create_lead()
        user = User.get(username="super_admin@test.com")
        device = ClientCreator.create_device()
        request = RegistrationTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            device_serial=device.composed_serial, 
            lead_id=lead.id

        )
        assert request.type == 'registration'
        assert json.loads(request.request_data) == {
            'device_serial': device.composed_serial,
            'lead_id': lead.id,
            'request_code': None,
            'contract_mobile_uuid': '',
            'partial_addon_delivery': None,
            'delivered_addons': None,
            'send_sms_to_client': False,
            'note': None
        }

        assert json.loads(request.answer_data)[0]['status'] == 'LEAD_INITIAL_PAYMENT_NOT_PAID'
        assert request.user.id == user.id


    @db_session
    def test_registration_transaction_fails_without__allocated_device(self):

        lead = ClientCreator.create_lead()
        lead.offer.linked_to_product = True
        user = User.get(username="super_admin@test.com")
        device = ClientCreator.create_device()
        with pytest.raises(Error) as error:
            request = RegistrationTransactionService.create(
                user=user,
                uuid=str(uuid.uuid1()),
                lead_id=lead.id
            )
            assert str(error.value) == 'A device could not be found with the serial number provided'
            assert request.user.id == user.id
        rollback()


    @db_session
    def test_registration_transaction_with_allocated_device(self):

        lead = ClientCreator.create_lead()
        user = User.get(username="super_admin@test.com")
        device = ClientCreator.create_device()
        device.allocated_lead = lead
        request = RegistrationTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            lead_id=lead.id
        )
        assert request.type == 'registration'
        assert json.loads(request.request_data) == {
            'device_serial': '',
            'lead_id': lead.id,
            'request_code': None,
            'contract_mobile_uuid': '',
            'partial_addon_delivery': None,
            'delivered_addons': None,
            'send_sms_to_client': False,
            'note': None
        }

        assert json.loads(request.answer_data)[0]['status'] == 'LEAD_INITIAL_PAYMENT_NOT_PAID'
        assert request.user.id == user.id