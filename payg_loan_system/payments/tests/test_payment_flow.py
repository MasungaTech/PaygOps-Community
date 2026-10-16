from datetime import datetime
from pony import orm
from config import API_PREFIX
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from messages_system.models.sms_db import OutgoingSMS
from core_system.users.services.user_getter_service import UserGetterService
from sales_system.leads.models.lead_status import LeadStatus
from sales_system.leads.models.status_category import StatusCategory
from sales_system.leads.services.add_lead_service import AddLeadService
from sales_system.leads.services.edit_lead_service import EditLeadService
from sales_system.lead_generator.model import LeadGenerator
from payg_loan_system.offers.services.create_offer_service import CreateOfferService
from payg_loan_system.contracts.services.contract_creation_service import ContractCreationService
from payg_loan_system.devices.services.create_device_service import DeviceCreateService


class TestPaymentFlow:

    client_id = None
    phone = "+2344567891234"
    test_count = 0
    
    @orm.db_session
    def test_payment_flow_base(self, api_client, good_api_key, gateway_api_key):
        self._create_client(api_client, good_api_key)
        data = {
            "transaction_id": "PAYMENT_FLOW_TEST_",
            "wallet_name": 'RANDOM WALLET ',
            "wallet_msisdn": "",
            "sent_datetime": datetime.now(),
            "memo": "",
            "amount": "1"
        }

        # Gateway payment
        data['wallet_msisdn'] = self.phone
        self._test_helper(data, api_client, gateway_api_key)

        data['wallet_msisdn'] = self.phone
        self._test_helper(data, api_client, good_api_key)

        data['wallet_msisdn'] = self.phone[1:]
        self._test_helper(data, api_client, good_api_key)

        data['wallet_msisdn'] = '00'+self.phone[1:]
        self._test_helper(data, api_client, good_api_key)

        data['amount'] = '1.'
        self._test_helper(data, api_client, good_api_key)

        data['amount'] = '1.0'
        self._test_helper(data, api_client, good_api_key)

        data['amount'] = '1.00'
        self._test_helper(data, api_client, good_api_key) 

        data['amount'] = '1.000'
        self._test_helper(data, api_client, good_api_key)

        data['amount'] = 1
        self._test_helper(data, api_client, good_api_key)

        data['amount'] = 1.
        self._test_helper(data, api_client, good_api_key)

        data['amount'] = 1.0
        self._test_helper(data, api_client, good_api_key)

        data['amount'] = 1.00
        self._test_helper(data, api_client, good_api_key)

        data['amount'] = 1.000
        self._test_helper(data, api_client, good_api_key)

        data['sent_datetime'] = '2020-04-01 20:20:20+10:00'
        self._test_helper(data, api_client, good_api_key)

        data['sent_datetime'] = '2020-04-01T20:20:20+10:00'
        self._test_helper(data, api_client, good_api_key)

        data['sent_datetime'] = '2020-04-01T20:20:20+1'
        self._test_helper(data, api_client, good_api_key)

        data['sent_datetime'] = '2020-04-01T20:20:20Z'
        self._test_helper(data, api_client, good_api_key)

        data['sent_datetime'] = '2020/04/01 20:20:20'
        self._test_helper(data, api_client, good_api_key)

        data['sent_datetime'] = '2020-04-01 20:20'
        self._test_helper(data, api_client, good_api_key)

        data['sent_datetime'] = '2020-04-01'
        self._test_helper(data, api_client, good_api_key)

    def _test_helper(self, data, api_client, good_api_key):
        self.test_count += 1
        data['transaction_id'] += 'TPF-'+str(self.test_count)
        data['wallet_name'] += str(self.test_count)
        response = self._post_payment(data, api_client, good_api_key)
        assert response.status_code == 201, response.get_json()
        sms = self._get_last_message()
        assert sms.ToNumber == self.phone
        assert '123 456 789' in sms.Body
        print(sms.Body)
        assert str(self.test_count+10)+'.00 USD' in sms.Body

    def _create_client(self, api_client, good_api_key):
        user = UserGetterService.get_by_username("super_admin@test.com")
        offer = CreateOfferService.add_from_data_and_user({
            "code": "PAYMENT_FLOW_TEST_OFFER",
            "name": "PAYMENT FLOW TEST OFFER",
            "type": "Loan",
            "downpayment": 10,
            "time_to_ownership_in_days": 365,
            "time_given_at_start_in_days": 0,
            "base_price_amount": 1,
            "raw_unit_cost": '',
            "family": 'Home',
            "base_price_time_in_days": 1,
            "automatic_unlock_code_sending": "True",
            "in_use_for_new_leads": "True",
            "can_be_approved_and_registered": "True"
        }, user)
        if not getattr(user.person, 'leadGenerator'):
            generator = LeadGenerator(person=user.person, type=2)
        else:
            generator = user.person.leadGenerator
        orm.flush()
        lead_data = {
            "village": OperationalEntitiesGetterService.get_list(user, level=0).first().not_empty_code,
            "name": "TestPayFlo",
            "surname": "WWW",
            "generator": generator.id,
            "status": 9,
            "gender": "Male",
            "offer": offer.id,
            "preferred_phone_number": self.phone
        }
        lead = AddLeadService.add_lead(lead_data, user)
        EditLeadService.edit_lead(lead, {
            "status": LeadStatus.get_first(StatusCategory.awaiting_payment).id,
        }, user)
        resp = self._post_payment({
            "transaction_id": "ABC-TESTDOWNPAYMENT",
            "sender_name": "TestPayFlo WWW",
            "sender_msisdn": self.phone,
            "amount": str(lead.offer.registration_fee)
        }, api_client, good_api_key)
        print(resp)
        device = DeviceCreateService.create(
            serial_number="123412343",
            device_type='1WY',
            mode=1
        )
        resp = ContractCreationService.create_from_lead_and_device(lead, device, user)
        print(resp)
        orm.flush()
        self.client_id = lead.contract.client.id
        return lead.contract.client

    @classmethod
    def _post_payment(cls, data, api_client, good_api_key):
        response = api_client.post(API_PREFIX + '/payments',
                                   json=data,
                                   headers={'Authorization': 'Bearer ' + good_api_key})
        return response

    @classmethod
    def _get_last_message(cls):
        with orm.db_session:
            last_message = orm.select(S for S in OutgoingSMS).order_by(orm.desc(OutgoingSMS.SendingTime)).first()
            return last_message
