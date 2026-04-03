from math import ceil
import uuid
from conftest import super_admin_user
from constants import NON_PAYG_TYPE
from core_system.operational_entities.models import Village
from datetime import datetime, timedelta
import dateutil
from mock import patch
from payg_loan_system.contracts.services.contract_termination_service import ContractTerminationService
from payg_loan_system.devices.model.device import Device
from payg_loan_system.devices.model.product_sub_type import ProductSubType
from payg_loan_system.transaction_requests.services.assign_device_service import AssignDeviceTransactionService
from payg_loan_system.transaction_requests.services.resume_contract_service import ResumeContractTransactionService
from pony import orm
from config import API_PREFIX
from core_system.users.services.user_getter_service import UserGetterService
from messages_system.models.sms_db import OutgoingSMS
from core_system.users.models.user_model import User
from payg_loan_system.contracts.models.addon_category import AddOnCategory
from payg_loan_system.contracts.models.addon_loan_extension_mode import AddOnLoanExtensionMode
from payg_loan_system.contracts.models.addons_model import AddOnType
from payg_loan_system.contracts.models.contract_event_model import ContractEvent, ContractEventType
from payg_loan_system.contracts.services.addon_service import AddonService
from payg_loan_system.contracts.services.addons.addon_offer_service import AddonOfferService
from payg_loan_system.contracts.services.contract_repayment_service import ContractRepaymentService
from payg_loan_system.devices.services.create_device_service import DeviceCreateService
from payg_loan_system.devices.device_api.device_api_request_service import DeviceAPIHelperV1
from payg_loan_system.transaction_requests.services.cancellation_service import CancelContractTransactionService
from payg_loan_system.transaction_requests.services.default_service import DefaultTransactionService
from payg_loan_system.transaction_requests.services.deregister_service import DeRegisterTransactionService
from payg_loan_system.transaction_requests.services.expected_paid_change_service import ExpectedPaidChangeTransactionService
from payg_loan_system.transaction_requests.services.swap_device_service import SwapDeviceTransactionService
from payg_loan_system.transaction_requests.services.undo_default_service import UndoDefaultTransactionService
from payg_loan_system.transaction_requests.services.pause_contract_service import PauseContractTransactionService
from sales_system.leads.models.lead import Lead
from shared.helpers.assert_datetime import assert_datetime
from shared.helpers.client_creator import ClientCreator


class TestScenario1:
    TEST_LEAD_ID = None
    TEST_CLIENT_ID = None
    AGENT_NUMBER = '+2349876543222'  # from the seeder
    CLIENT_NUMBER_1 = '+2341112223330'
    CLIENT_NUMBER_2 = '+2342223334440'
    DEPOSIT_PAYMENT_REFERENCE = 'SCENARIO1_PAY1'
    PAYMENT_ACCOUNT_NAME = 'SCENARIO1_ACCOUNT_1'
    PAYMENT_ACCOUNT_NAME_2 = 'SCENARIO1_ACCOUNT_2'
    PAYMENT_ACCOUNT_NAME_3 = 'SCENARIO1_ACCOUNT_3'
    TEST_DEVICE_REFERENCE = 'NPG-888'
    DEPOSIT_PAYMENT_REFERENCE_LEAD2 = 'SCENARIO1_PAYL2-1'
    TEST_LEAD_2_ID = None
    TEST_CLIENT_2_ID = None
    CLIENT_NUMBER_3 = '+2348883334440'
    TEST_LEAD_3_ID = None
    TEST_CLIENT_3_ID = None
    CLIENT_NUMBER_4 = '+2349993334440'
    DEPOSIT_PAYMENT_REFERENCE_LEAD3 = 'SCENARIO1_PAYL3-1'
    PAYMENT_ACCOUNT_NAME_4 = 'SCENARIO1_ACCOUNT_4'
    PAYEMENT_WALLET_OPERATOR = 'MPESA'

    def test_setup(self):
        with orm.db_session:
            this_user = orm.select(user for user in User).first()
            this_device = DeviceCreateService.create(
                serial_number='888',
                device_type='NPG',
                mode=1,
            )

    @classmethod
    def _post_data(cls, data, route, api_client, admin_api_key):
        response = api_client.post(API_PREFIX + route,
                                   json=data,
                                   headers={'Authorization': 'Bearer ' + admin_api_key})
        return response

    @classmethod
    def _get_data(cls, route, api_client, admin_api_key, params=None):
        response = api_client.get(API_PREFIX + route,
                                  headers={'Authorization': 'Bearer ' + admin_api_key},
                                  query_string=params)
        return response

    @classmethod
    def _check_if_data_in_dict_match(cls, dict1, dict2):
        for key, dict1_value in dict1.items():
            if isinstance(dict1_value, list):
                assert sorted(dict2.get(key)) == sorted(dict1_value)
            else:
                assert dict2.get(key) == dict1_value

    @classmethod
    def _get_last_message(cls):
        with orm.db_session:
            last_message = orm.select(
                s for s in OutgoingSMS
            ).order_by(orm.desc(OutgoingSMS.SendingTime)).first()
            return last_message.Body

    @classmethod
    def _get_last_messages(cls, number=3):
        with orm.db_session:
            last_messages = orm.select(
                s for s in OutgoingSMS
            ).order_by(orm.desc(OutgoingSMS.SendingTime))[:number]
            return ' '.join([l.Body for l in last_messages])

    def _get_client_data(self, api_client, admin_api_key, client_id=None):
        if not client_id:
            client_id = self.__class__.TEST_CLIENT_ID
        return self._get_data('/clients/simple_list', api_client, admin_api_key,
                              {'client_id': client_id})

    def _get_client_expiration_date(self, api_client, admin_api_key, client_id=None):
        client_data = self._get_client_data(api_client, admin_api_key, client_id)
        client_date_str = client_data.json[0].get('client_next_payment_due')
        return dateutil.parser.parse(client_date_str).replace(tzinfo=None)

    @orm.db_session
    def test_add_lead_full_data(self, api_client, admin_api_key):
        lead_data = {
            'name': 'Scenario1',
            'surname': 'Client',
            'village': Village.select().first().not_empty_code,
            'generator': 1,
            'status': 'Ready to Buy',
            'generation_date': '2018-12-13T14:32:22Z',
            'status_comment': 'Its a good lead!',
            'next_contact': '2018-12-17T14:32:22Z',
            'reasons_for_not_buying': ['Waiting for other income', 'Need to speak to family'],
            'offer': 889,
            'home': True,
            'business': True,
            'gender': 'Male',
            'birthdate': '1991-02-21T14:32:22Z',
            'gps_longitude': 1.2,
            'gps_latitude': 1.3,
            'phone_numbers': [self.CLIENT_NUMBER_1, self.CLIENT_NUMBER_2],
            'preferred_phone_number': self.CLIENT_NUMBER_1,
            "promised_to_pay_date": "2019-01-08T00:00:00Z",
            "planned_delivery_date": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "commission": 1234,
            "commission_note": "Regular comission",
            "portfolio": 1,
            "sms_language": "EN",
            "verbal_language": "Pirate English"
        }
        response = self._post_data(lead_data, '/leads', api_client, admin_api_key)
        assert response.status_code == 201
        expected_data = lead_data
        expected_data.update({'status': 'Awaiting Payment'})
        expected_data.update({'status_comment': 'Automatically Approved'})
        self._check_if_data_in_dict_match(expected_data, response.json)
        self.__class__.TEST_LEAD_ID = response.json['id']

    @orm.db_session
    def test_add_payment(self, api_client, admin_api_key, super_admin_user):
        payment_data = {
            "reference": self.DEPOSIT_PAYMENT_REFERENCE,
            "amount": 52000,
            "sender_name": self.PAYMENT_ACCOUNT_NAME,
            "sender_msisdn": self.CLIENT_NUMBER_1,  # Same as the lead we made
            "wallet_operator": self.PAYEMENT_WALLET_OPERATOR
        }
        response = self._post_data(payment_data, '/payments', api_client, admin_api_key)
        assert response.status_code == 201

        response = self._get_data('/leads/' + str(self.__class__.TEST_LEAD_ID), api_client, admin_api_key)
        assert response.status_code == 200
        assert response.json.get('status') == 'Awaiting Delivery'

        response = self._get_data('/leads/'+str(self.__class__.TEST_LEAD_ID), api_client, admin_api_key)
        assert response.status_code == 200
        lead_installation_reference = response.json.get('future_contract_reference')

        sms_to_send = 'Register#'+self.TEST_DEVICE_REFERENCE+'*'+lead_installation_reference
        message_data = {
            "uuid": "test-message-scenario1-1",
            "from_number": self.AGENT_NUMBER,
            "to_number": "TESTING",
            "body": sms_to_send
        }
        response = self._post_data(message_data, '/messages', api_client, admin_api_key)
        assert response.status_code == 200

        response = self._get_data('/leads/' + str(self.__class__.TEST_LEAD_ID), api_client, admin_api_key)
        client_id = response.json.get('client')
        self.__class__.TEST_CLIENT_ID = client_id
        assert response.status_code == 200
        assert response.json.get('status') == 'Installed'
        assert client_id is not None

        # With the payment of 52000 made, this should pay for the 50000 deposit which gives 1 week of free time
        # and then 2 weeks at 1000 a week, so we expect 3 weeks paid in total
        last_message = self._get_last_message()
        assert 'You have paid 52000.00 USD' in last_message
        assert_datetime(self._get_client_expiration_date(api_client, admin_api_key),
                        datetime.now()+timedelta(days=3*7), seconds=2)

    def test_add_payment_2(self, api_client, admin_api_key):
        payment_data = {
            "reference": 'SCENARIO1_PAY2',
            "amount": 1000,
            "sender_name": self.PAYMENT_ACCOUNT_NAME,
            "sender_msisdn": self.CLIENT_NUMBER_1  # Same as the lead we made
        }
        response = self._post_data(payment_data, '/payments', api_client, admin_api_key)
        assert response.status_code == 201

        # With the 1000 payments, this should add 1 week
        last_message = self._get_last_message()
        assert 'You have paid 53000.00 USD' in last_message
        assert_datetime(self._get_client_expiration_date(api_client, admin_api_key),
                        datetime.now()+timedelta(days=4*7), seconds=5)

    def test_add_payment_3_test_autolink_second_account(self, api_client, admin_api_key):
        payment_data = {
            "reference": 'SCENARIO1_PAY3',
            "amount": 4000,
            "sender_name": self.PAYMENT_ACCOUNT_NAME_2,
            "sender_msisdn": self.CLIENT_NUMBER_2  # Same as the lead we made
        }
        response = self._post_data(payment_data, '/payments', api_client, admin_api_key)
        assert response.status_code == 201

        # With the 4000 payments, this should add 4 weeks + 2 days (30 days)
        last_message = self._get_last_message()
        assert 'You have paid 57285.71 USD' in last_message
        assert_datetime(self._get_client_expiration_date(api_client, admin_api_key),
                        datetime.now()+timedelta(days=8*7+2), seconds=5)

    def test_add_payment_4(self, api_client, admin_api_key):
        payment_data = {
            "reference": 'SCENARIO1_PAY4',
            "amount": 6000,
            "sender_name": self.PAYMENT_ACCOUNT_NAME,
            "sender_msisdn": self.CLIENT_NUMBER_1  # Same as the lead we made
        }
        response = self._post_data(payment_data, '/payments', api_client, admin_api_key)
        assert response.status_code == 201

        # With the 6000 payments, this should add 6 weeks + 3 days (45 days)
        last_message = self._get_last_message()
        assert 'You have paid 63714.28 USD' in last_message
        assert_datetime(self._get_client_expiration_date(api_client, admin_api_key),
                        datetime.now()+timedelta(days=14*7+5), seconds=10)

    def test_give_delay(self, api_client, admin_api_key):
        sms_to_send = 'GiveDelay#'+self.TEST_DEVICE_REFERENCE+'*1'
        message_data = {
            "uuid": "test-message-scenario1-2",
            "from_number": self.AGENT_NUMBER,
            "to_number": "TESTING",
            "body": sms_to_send
        }
        response = self._post_data(message_data, '/messages', api_client, admin_api_key)
        assert response.status_code == 200
        # There should be one more day in the expiration date
        assert_datetime(self._get_client_expiration_date(api_client, admin_api_key),
                        datetime.now()+timedelta(days=14*7+6), seconds=5)

    def test_give_discount(self, api_client, admin_api_key):
        sms_to_send = 'GiveDiscount#'+self.TEST_DEVICE_REFERENCE+'*1'
        message_data = {
            "uuid": "test-message-scenario1-3",
            "from_number": self.AGENT_NUMBER,
            "to_number": "TESTING",
            "body": sms_to_send
        }
        response = self._post_data(message_data, '/messages', api_client, admin_api_key)
        assert response.status_code == 200
        # There should be one more day in the expiration date and the days paid
        last_message = self._get_last_message()
        assert '14 weeks and 6 days' in last_message  # We had 14 weeks and 5 days paid before and we add 1
        assert_datetime(self._get_client_expiration_date(api_client, admin_api_key),
                        datetime.now()+timedelta(days=15*7), seconds=5)

    def test_give_negative_discount(self, api_client, admin_api_key):
        sms_to_send = 'GiveDiscount#'+self.TEST_DEVICE_REFERENCE+'*-1'
        message_data = {
            "uuid": "test-message-scenario1-4",
            "from_number": self.AGENT_NUMBER,
            "to_number": "TESTING",
            "body": sms_to_send
        }
        response = self._post_data(message_data, '/messages', api_client, admin_api_key)
        assert response.status_code == 200
        last_message = self._get_last_message()
        assert '14 weeks and 5 days' in last_message  # We had 14 weeks and 6 days paid before and we remove 1
        assert_datetime(self._get_client_expiration_date(api_client, admin_api_key),
                        datetime.now()+timedelta(days=14*7+6), seconds=5)

    def test_give_negative_delay(self, api_client, admin_api_key):
        sms_to_send = 'GiveDelay#'+self.TEST_DEVICE_REFERENCE+'*-1'
        message_data = {
            "uuid": "test-message-scenario1-5",
            "from_number": self.AGENT_NUMBER,
            "to_number": "TESTING",
            "body": sms_to_send
        }
        response = self._post_data(message_data, '/messages', api_client, admin_api_key)
        assert response.status_code == 200
        last_message = self._get_last_message()
        # We had 14 weeks and 6 days paid before and we remove 1
        assert 'delay of -1 days was granted successfully' in last_message
        assert_datetime(self._get_client_expiration_date(api_client, admin_api_key),
                        datetime.now()+timedelta(days=14*7+5), seconds=10)

    def test_give_negative_discount_more_than_paid(self, api_client, admin_api_key):
        sms_to_send = 'GiveDiscount#'+self.TEST_DEVICE_REFERENCE+'*-'+str(15*7)
        message_data = {
            "uuid": "test-message-scenario1-6",
            "from_number": self.AGENT_NUMBER,
            "to_number": "TESTING",
            "body": sms_to_send
        }
        response = self._post_data(message_data, '/messages', api_client, admin_api_key)
        assert response.status_code == 200
        last_message = self._get_last_message()
        assert 'negative discount failed' in last_message  # We had 14 weeks and 6 days paid before and we remove 1
        assert_datetime(self._get_client_expiration_date(api_client, admin_api_key),
                        datetime.now()+timedelta(days=14*7+5), seconds=10)

    def test_change_similar_pricing(self, api_client, admin_api_key):
        sms_to_send = 'ChangeOffer#'+self.TEST_DEVICE_REFERENCE+'*TOG3'
        message_data = {
            "uuid": "test-message-scenario1-7",
            "from_number": self.AGENT_NUMBER,
            "to_number": "TESTING",
            "body": sms_to_send
        }
        response = self._post_data(message_data, '/messages', api_client, admin_api_key)
        assert response.status_code == 200
        last_message = self._get_last_message()
        assert 'successfully' in last_message
        assert ' 14 weeks and 5 days' in last_message  # should not have changed  since the new offer has the same pricing
        assert_datetime(self._get_client_expiration_date(api_client, admin_api_key),
                        datetime.now()+timedelta(days=14*7+5), seconds=10)

    def test_change_new_offer_deposit_more_than_paid(self, api_client, admin_api_key):
        sms_to_send = 'ChangeOffer#'+self.TEST_DEVICE_REFERENCE+'*TOG4'
        message_data = {
            "uuid": "test-message-scenario1-8",
            "from_number": self.AGENT_NUMBER,
            "to_number": "TESTING",
            "body": sms_to_send
        }
        response = self._post_data(message_data, '/messages', api_client, admin_api_key)
        assert response.status_code == 200
        last_message = self._get_last_message()
        assert 'offer change failed because the total amount paid on the ' \
               'previous offer is below the downpayment amount of the new offer' in last_message
        assert_datetime(self._get_client_expiration_date(api_client, admin_api_key),
                        datetime.now()+timedelta(days=14*7+5), seconds=10)

    def test_add_payment_5(self, api_client, admin_api_key):
        payment_data = {
            "reference": 'SCENARIO1_PAY5',
            "amount": 40400,  # This should be equivalent to 303 days, or 43 weeks and 2 days
            "sender_name": self.PAYMENT_ACCOUNT_NAME,
            "sender_msisdn": self.CLIENT_NUMBER_1  # Same as the lead we made
        }
        response = self._post_data(payment_data, '/payments', api_client, admin_api_key)
        assert response.status_code == 201
        last_message = self._get_last_message()
        assert 'You have paid 106999.99 USD' in last_message  # 14 weeks and 5 days + 43 weeks and 2 days = 58 weeks
        assert_datetime(self._get_client_expiration_date(api_client, admin_api_key),
                        datetime.now()+timedelta(days=58*7), seconds=10)

    def test_change_offer_valid(self, api_client, admin_api_key):
        sms_to_send = 'ChangeOffer#'+self.TEST_DEVICE_REFERENCE+'*TOG4'
        message_data = {
            "uuid": "test-message-scenario1-9",
            "from_number": self.AGENT_NUMBER,
            "to_number": "TESTING",
            "body": sms_to_send
        }
        response = self._post_data(message_data, '/messages', api_client, admin_api_key)
        assert response.status_code == 200
        last_message = self._get_last_message()
        assert 'successfully' in last_message
        # 57000 + 50000 deposit paid on last offer, turn into 7000 + 100000 deposit paid on new offer: 7 weeks (+1 free)
        assert '8 weeks and 0 days' in last_message
        assert_datetime(self._get_client_expiration_date(api_client, admin_api_key),
                        datetime.now()+timedelta(days=58*7), seconds=10)
        # Should not change because weekly price is the same and we currently do not account for the deposit

    def test_add_payment_6(self, api_client, admin_api_key):
        payment_data = {
            "reference": 'SCENARIO1_PAY6',
            "amount": 2000,
            "sender_name": self.PAYMENT_ACCOUNT_NAME,
            "sender_msisdn": self.CLIENT_NUMBER_1  # Same as the lead we made
        }
        response = self._post_data(payment_data, '/payments', api_client, admin_api_key)
        assert response.status_code == 201
        last_message = self._get_last_message()
        assert 'You have paid 108999.99 USD' in last_message  # 2 weeks at 1000 each
        assert_datetime(self._get_client_expiration_date(api_client, admin_api_key),
                        datetime.now()+timedelta(days=60*7), seconds=10)
        # should increase by  1 week

    def test_change_offer_valid_2(self, api_client, admin_api_key):
        sms_to_send = 'ChangeOffer#'+self.TEST_DEVICE_REFERENCE+'*TOG5'
        message_data = {
            "uuid": "test-message-scenario1-10",
            "from_number": self.AGENT_NUMBER,
            "to_number": "TESTING",
            "body": sms_to_send
        }
        response = self._post_data(message_data, '/messages', api_client, admin_api_key)
        assert response.status_code == 200
        last_message = self._get_last_message()
        assert 'successfully' in last_message
        # 9000 + 100000 deposit paid turn into 100000 deposit and 6 weeks at 1500 (+1 free week in both cases)
        assert '7 weeks and 0 days' in last_message
        assert_datetime(self._get_client_expiration_date(api_client, admin_api_key),
                        datetime.now()+timedelta(days=60*7), seconds=10)
        # should not change

    def test_change_offer_valid_3(self, api_client, admin_api_key):
        sms_to_send = 'ChangeOffer#'+self.TEST_DEVICE_REFERENCE+'*TOG4'
        message_data = {
            "uuid": "test-message-scenario1-11",
            "from_number": self.AGENT_NUMBER,
            "to_number": "TESTING",
            "body": sms_to_send
        }
        response = self._post_data(message_data, '/messages', api_client, admin_api_key)
        assert response.status_code == 200
        last_message = self._get_last_message()
        assert 'successfully' in last_message
        # Should be the same as before the first change
        assert '10 weeks and 0 days' in last_message
        assert_datetime(self._get_client_expiration_date(api_client, admin_api_key),
                        datetime.now()+timedelta(days=60*7), seconds=10)
        # should not change

    def test_change_device(self, api_client, admin_api_key):
        sms_to_send = 'ChangeDevice#'+self.TEST_DEVICE_REFERENCE+'*NON_PAYG_DEVICE'
        message_data = {
            "uuid": "test-message-scenario1-12",
            "from_number": self.AGENT_NUMBER,
            "to_number": "TESTING",
            "body": sms_to_send
        }
        response = self._post_data(message_data, '/messages', api_client, admin_api_key)
        assert response.status_code == 200
        last_message = self._get_last_message()
        assert 'successfully' in last_message
        # Should be the same as before the first change
        assert_datetime(self._get_client_expiration_date(api_client, admin_api_key),
                        datetime.now()+timedelta(days=60*7), seconds=10)

    def test_add_payment_fully_paid(self, api_client, admin_api_key):
        payment_data = {
            "reference": 'SCENARIO1_PAY7',
            "amount": 84000,
            "sender_name": self.PAYMENT_ACCOUNT_NAME,
            "sender_msisdn": self.CLIENT_NUMBER_1  # Same as the lead we made
        }
        response = self._post_data(payment_data, '/payments', api_client, admin_api_key)
        assert response.status_code == 201
        last_message = self._get_last_messages()
        # He had paid 9000 + 100000 before, so there is 90,000 left to pay
        # 14 payments of 6000 = 84000, each giving 6000 paid + (1500/7)*2 of discount, so total of 6000 discount (equivalent to 4 weeks paid full time)
        # Equivalent to 56 weeks + 4 weeks free
        assert 'You have now completed all of your payments' in last_message

    def test_deregister_wrong_device(self, api_client, admin_api_key):
        sms_to_send = 'Deregister#'+self.TEST_DEVICE_REFERENCE  # This device is not owned by the client since the device change
        message_data = {
            "uuid": "test-message-scenario1-13",
            "from_number": self.AGENT_NUMBER,
            "to_number": "TESTING",
            "body": sms_to_send
        }
        response = self._post_data(message_data, '/messages', api_client, admin_api_key)
        assert response.status_code == 200
        last_message = self._get_last_message()
        assert 'does not belong to any client' in last_message

    @orm.db_session
    def test_add_lead_2(self, api_client, admin_api_key):
        lead_data = {
            'name': 'Scenario1',
            'surname': 'Client2',
            'village': Village.select().first().not_empty_code,
            'generator': 1,
            'status': 'Ready to Buy',
            'generation_date': '2018-12-13T14:32:22Z',
            'status_comment': 'Its a good lead!',
            'next_contact': '2018-12-17T14:32:22Z',
            'reasons_for_not_buying': ['Waiting for other income', 'Need to speak to family'],
            'offer': 889,
            'home': True,
            'business': True,
            'gender': 'Male',
            'birthdate': '1991-02-21T14:32:22Z',
            'gps_longitude': 1.2,
            'gps_latitude': 1.3,
            'phone_numbers': [self.CLIENT_NUMBER_3],
            'preferred_phone_number': self.CLIENT_NUMBER_3,
            "promised_to_pay_date": "2019-01-08T00:00:00Z",
            "planned_delivery_date": "2019-01-10T00:00:00Z",
            "commission": 1234,
            "commission_note": "Regular comission",
            "portfolio": 1,
            "sms_language": "EN",
            "verbal_language": "Pirate English"
        }
        response = self._post_data(lead_data, '/leads', api_client, admin_api_key)
        assert response.status_code == 201
        expected_data = lead_data
        expected_data.update({'status': 'Awaiting Payment'})
        expected_data.update({'status_comment': 'Automatically Approved'})
        self._check_if_data_in_dict_match(expected_data, response.json)
        self.__class__.TEST_LEAD_2_ID = response.json['id']

    def test_add_payment_lead2(self, api_client, admin_api_key):
        payment_data = {
            "reference": self.DEPOSIT_PAYMENT_REFERENCE_LEAD2,
            "amount": 52000,
            "sender_name": self.PAYMENT_ACCOUNT_NAME_3,
            "sender_msisdn": self.CLIENT_NUMBER_3  # Same as the lead we made
        }
        response = self._post_data(payment_data, '/payments', api_client, admin_api_key)
        assert response.status_code == 201

        response = self._get_data('/leads/' + str(self.__class__.TEST_LEAD_2_ID), api_client, admin_api_key)
        assert response.status_code == 200
        assert response.json.get('status') == 'Awaiting Delivery'

    def test_register_lead_2_sms(self, api_client, admin_api_key):
        response = self._get_data('/leads/'+str(self.__class__.TEST_LEAD_2_ID), api_client, admin_api_key)
        assert response.status_code == 200
        lead_installation_reference = response.json.get('future_contract_reference')

        sms_to_send = 'Register#'+self.TEST_DEVICE_REFERENCE+'*'+lead_installation_reference
        message_data = {
            "uuid": "test-message-scenario1-register-lead-234234",
            "from_number": self.AGENT_NUMBER,
            "to_number": "TESTING",
            "body": sms_to_send
        }
        response = self._post_data(message_data, '/messages', api_client, admin_api_key)
        assert response.status_code == 200

        response = self._get_data('/leads/' + str(self.__class__.TEST_LEAD_2_ID), api_client, admin_api_key)
        client_id = response.json.get('client')
        self.__class__.TEST_CLIENT_2_ID = client_id
        assert response.status_code == 200
        assert response.json.get('status') == 'Installed'
        assert client_id is not None

        # With the payment of 52000 made, this should pay for the 50000 deposit which gives 1 week of free time
        # and then 2 weeks at 1000 a week, so we expect 3 weeks paid in total
        last_message = self._get_last_message()
        assert 'You have paid 52000.00 USD' in last_message
        assert_datetime(
            self._get_client_expiration_date(api_client, admin_api_key, client_id=self.__class__.TEST_CLIENT_2_ID),
            datetime.now()+timedelta(days=3*7), seconds=5)

    def test_paycash_client_2(self, api_client, admin_api_key):
        sms_to_send = 'PayCash#'+self.TEST_DEVICE_REFERENCE+'*1000'
        message_data = {
            "uuid": "test-message-scenario1-15",
            "from_number": self.AGENT_NUMBER,
            "to_number": "TESTING",
            "body": sms_to_send
        }
        response = self._post_data(message_data, '/messages', api_client, admin_api_key)
        assert response.status_code == 200
        last_message = self._get_last_message()
        assert 'A cash payment of 1000 USD was marked as collected' in last_message

        # With the payment of 52000 made, this should pay for the 50000 deposit which gives 1 week of free time
        # and then 2 weeks at 1000 a week, so we expect 3 weeks paid in total
        last_message = self._get_last_message()
        assert 'You have paid 53000.00 USD' in last_message
        assert_datetime(
            self._get_client_expiration_date(api_client, admin_api_key, client_id=self.__class__.TEST_CLIENT_2_ID),
            datetime.now()+timedelta(days=4*7), seconds=5)

    def test_deregister_client_2(self, api_client, admin_api_key):
        sms_to_send = 'Deregister#'+self.TEST_DEVICE_REFERENCE  # This device should now belong to client 2
        message_data = {
            "uuid": "test-message-scenario1-16",
            "from_number": self.AGENT_NUMBER,
            "to_number": "TESTING",
            "body": sms_to_send
        }
        response = self._post_data(message_data, '/messages', api_client, admin_api_key)
        assert response.status_code == 200
        last_message = self._get_last_message()
        assert 'successfully' in last_message

    # New test with decimal amounts

    @orm.db_session
    def test_add_lead_3(self, api_client, admin_api_key):
        lead_data = {
            'name': 'Scenario1',
            'surname': 'Client3',
            'village': Village.select().first().not_empty_code,
            'generator': 1,
            'status': 'Ready to Buy',
            'generation_date': '2018-12-13T14:32:22Z',
            'status_comment': 'Its a good lead!',
            'next_contact': '2018-12-17T14:32:22Z',
            'reasons_for_not_buying': ['Waiting for other income', 'Need to speak to family'],
            'offer': 893,
            'home': True,
            'business': True,
            'gender': 'Male',
            'birthdate': '1991-02-21T14:32:22Z',
            'gps_longitude': 1.2,
            'gps_latitude': 1.3,
            'phone_numbers': [self.CLIENT_NUMBER_4],
            'preferred_phone_number': self.CLIENT_NUMBER_4,
            "promised_to_pay_date": "2019-01-08T00:00:00Z",
            "planned_delivery_date": "2019-01-10T00:00:00Z",
            "commission": 1234,
            "commission_note": "Regular comission",
            "portfolio": 1,
            "sms_language": "EN",
            "verbal_language": "Pirate English"
        }
        print(Village.select().first().not_empty_code)
        response = self._post_data(lead_data, '/leads', api_client, admin_api_key)
        assert response.status_code == 201
        expected_data = lead_data
        expected_data.update({'status': 'Awaiting Payment'})
        expected_data.update({'status_comment': 'Automatically Approved'})
        self._check_if_data_in_dict_match(expected_data, response.json)
        self.__class__.TEST_LEAD_3_ID = response.json['id']

    def test_add_payment_lead3(self, api_client, admin_api_key):
        payment_data = {
            "reference": self.DEPOSIT_PAYMENT_REFERENCE_LEAD3,
            "amount": 6.5,  # This is for 1.5 deposit + 2 weeks for 5000
            "sender_name": self.PAYMENT_ACCOUNT_NAME_4,
            "sender_msisdn": self.CLIENT_NUMBER_4  # Same as the lead we made
        }
        response = self._post_data(payment_data, '/payments', api_client, admin_api_key)
        assert response.status_code == 201

    def test_lead_3_payment_success(self, api_client, admin_api_key):
        response = self._get_data('/leads/' + str(self.__class__.TEST_LEAD_3_ID), api_client, admin_api_key)
        assert response.status_code == 200
        assert response.json.get('status') == 'Awaiting Delivery'

    def test_register_lead_3_sms(self, api_client, admin_api_key):
        response = self._get_data('/leads/'+str(self.__class__.TEST_LEAD_3_ID), api_client, admin_api_key)
        assert response.status_code == 200
        lead_installation_reference = response.json.get('future_contract_reference')

        sms_to_send = 'Register#'+self.TEST_DEVICE_REFERENCE+'*'+lead_installation_reference
        message_data = {
            "uuid": "test-message-scenario1-17",
            "from_number": self.AGENT_NUMBER,
            "to_number": "TESTING",
            "body": sms_to_send
        }
        response = self._post_data(message_data, '/messages', api_client, admin_api_key)
        assert response.status_code == 200

    def test_lead_3_registration_success(self, api_client, admin_api_key):
        response = self._get_data('/leads/' + str(self.__class__.TEST_LEAD_3_ID), api_client, admin_api_key)
        client_id = response.json.get('client')
        self.__class__.TEST_CLIENT_3_ID = client_id
        assert response.status_code == 200
        assert response.json.get('status') == 'Installed'
        assert client_id is not None

    def test_proper_number_of_weeks_activated_lead4(self, api_client, admin_api_key):
        # With the payment of 6.5 made, this should pay for the 1.5 deposit which gives 1 week of free time
        # and then 2 weeks for 2.5 a week, so we expect 3 weeks paid in total
        last_message = self._get_last_message()
        assert '6.50 USD' in last_message
        assert_datetime(
            self._get_client_expiration_date(api_client, admin_api_key, client_id=self.__class__.TEST_CLIENT_3_ID),
            datetime.now()+timedelta(days=3*7), seconds=5)

    def test_paycash_client_3(self, api_client, admin_api_key):
        sms_to_send = 'PayCash#'+self.TEST_DEVICE_REFERENCE+'*10'
        message_data = {
            "uuid": "test-message-scenario1-18",
            "from_number": self.AGENT_NUMBER,
            "to_number": "TESTING",
            "body": sms_to_send
        }
        response = self._post_data(message_data, '/messages', api_client, admin_api_key)
        assert response.status_code == 200
        last_message = self._get_last_message()
        assert 'A cash payment of 10 USD was marked as collected' in last_message

    def test_proper_number_of_weeks_activated_lead5(self, api_client, admin_api_key):
        # and then 5 weeks for 10 USD, so we expect 8 weeks paid in total
        last_message = self._get_last_message()
        assert 'You have paid 19.00 USD' in last_message
        assert_datetime(
            self._get_client_expiration_date(api_client, admin_api_key, client_id=self.__class__.TEST_CLIENT_3_ID),
            datetime.now()+timedelta(days=8*7), seconds=5)


    @orm.db_session
    def test_contract_events_narration(self, api_client, good_api_key):

        user = UserGetterService.get_by_username("super_admin@test.com")
        contract = ClientCreator.create(
            api_client, good_api_key, extra_paid=365
        ).contracts.select().first()
        product = ProductSubType(
            name='test',
            sku='test-123',
            device_type='NPG',
            is_serialized=True
        )
        device = DeviceCreateService.create(
                serial_number='9988',
                device_type='NPG',
                mode=1,
                product_sub_type=product.name
        )
        device2 = DeviceCreateService.create(
                serial_number='9989',
                device_type='NPG',
                mode=1,
                product_sub_type=product.name
        )
        offer = AddonOfferService.create(
            user,
            "OFFER TEST EXTENSION DAYS",
            "OFFERduration",
            "10",
            AddOnCategory.get(name="Product"),
            AddOnType.loan,
            available=True,
            loan_mode=AddOnLoanExtensionMode.duration, # to confirm with @Ben since this is wierd changed this from duration to amount
            downpayment="3",
            linked_to_product=True,
            product_sub_type_id=product.id
        )
        addon = AddonService.create(
            contract, offer.last_version, 1, user, device_serial=device.composed_serial
        )
        AddonService.cancel(addon, user)

        offer2 = AddonOfferService.create(
            user,
            "OFFER TEST amount DAYS",
            "OFFEramount",
            "10",
            AddOnCategory.get(name="Product"),
            AddOnType.loan,
            available=True,
            loan_mode=AddOnLoanExtensionMode.amount,
            downpayment="3"
        )
        addon = AddonService.create(
            contract, offer2.last_version, 1, user, planned_delivery_date=datetime.now()+timedelta(days=1)
        )

        DefaultTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            device_serial=contract.linked_device.composed_serial
        )

        UndoDefaultTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            device_serial=contract.linked_device.composed_serial
        )

        ExpectedPaidChangeTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            adjustment_amount=1
        )

        print(f"contract.repayments.select().order_by(lambda r: orm.desc(r.time)).first(): {contract.repayments.select().order_by(lambda r: orm.desc(r.time)).first()}")
        print(f"contract: {contract.repayments.select().order_by(lambda r: orm.desc(r.time)).first().contract}")
        print(f"contract.addons: {list(contract.repayments.select().order_by(lambda r: orm.desc(r.time)).first().contract.add_ons.select(lambda a: a.offer_version.offer.type != AddOnType.lump_sum).order_by(lambda a: a.offer_version.downpayment < 0))}")

        ContractRepaymentService.reverse_repayment(contract.repayments.select().order_by(lambda r: orm.desc(r.time)).first())
        PauseContractTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            note="test narration"
        )

        ResumeContractTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
            note="test narration"
        )

        addon = AddonService.create(contract, offer.last_version, 1, user, device_serial=device.composed_serial, delivered=True)

        
        addon = AddonService.create(contract, offer.last_version, 1, user, device_serial=device.composed_serial, delivered=True)

        offer3 = AddonOfferService.create(
            user,
            "Maize produce purchasing addon",
            "MPROD",
            "10000",
            AddOnCategory.get(name="Purchasing"),
            AddOnType.lump_sum,
            available=True,
            purchasing_addon=True,
            need_approval=True
        )
        device_data = {'serial_number':'9990','device_type':'NPG','mode':1,'product_sub_type':product.name}
        contract2 = ClientCreator.create(api_client, good_api_key, device_data=device_data, extra_paid=0).contracts.select().first()
        addon = AddonService.create(contract2, offer3.last_version, ceil(contract.get_outstanding_balance()/10000)+1, user, planned_delivery_date=datetime.now()+timedelta(days=1))
        AddonService.approve(addon, user)
        addon2 = AddonService.create(contract, offer.last_version, 1, user, device_serial=device.composed_serial, delivered=True)
        swap_data = {
            'new_device': device2, 'client': contract2.client, 'contract': contract2, 'contract_addon':addon2,
            'old_request_code':None, 'new_request_code':None,
        }
        SwapDeviceTransactionService._process(
            user=user,
            uuid=str(uuid.uuid1()),
            offline=True,
            time=datetime.now(),
            **swap_data
        )
        swap_data.update({'new_device':device})
        AssignDeviceTransactionService._process(
            user=user,
            uuid=str(uuid.uuid1()),
            offline=True,
            time=datetime.now(),
            **swap_data
        )
        
        CancelContractTransactionService.create(
            user=user,
            uuid=str(uuid.uuid1()),
            contract_reference=contract.reference,
        )
        for event_type in ContractEventType.to_list():
            event = ContractEvent.select(lambda ce: ce.type == event_type).first()
            if not event:
                raise Exception(f'No event of type {event_type} to test narration')
            event.get_narration()
