from core_system.operational_entities.models import Village
from shared.logger.loggers import Error
from pony.orm import db_session
from config import API_PREFIX
from sales_system.leads.models.lead_status import LeadStatus
from sales_system.leads.models.status_category import StatusCategory
from sales_system.leads.models.lead import Lead
from mock import Mock


class TestEditLead:
    TEST_LEAD_ID = None

    def _post_edit_data(self, lead_id, lead_data, api_client, admin_api_key):
        response = api_client.post(API_PREFIX + '/leads/'+str(lead_id),
                                   json=lead_data,
                                   headers={'Authorization': 'Bearer ' + admin_api_key})
        return response

    @classmethod
    def _check_if_data_in_dict_match(cls, dict1, dict2):
        for key, dict1_value in dict1.items():
            if isinstance(dict1_value, list):
                assert sorted(dict2.get(key)) == sorted(dict1_value)
            else:
                assert dict2.get(key) == dict1_value

    # We use this instead of regular setup class to be able to use fixtures
    @db_session
    def test_setup(self, api_client, admin_api_key):
        # We create a lead
        lead_data = {
            'name': 'Example',
            'surname': 'EditLead',
            'village': Village.select().first().not_empty_code,
            'generator': 1,
            "gender": "Male",
            'status': 14,
            'preferred_phone_number': '+2341234123413'
        }
        response = api_client.post(API_PREFIX + '/leads',
                                   json=lead_data,
                                   headers={'Authorization': 'Bearer ' + admin_api_key})
        self.__class__.TEST_LEAD_ID = response.json['id']
        assert self.__class__.TEST_LEAD_ID is not None

    def test_edit_lead_add_phone_number(self, api_client, admin_api_key):
        lead_data = {
            'phone_numbers': ['+2342223334448'],
            'preferred_phone_number': '+2342223334448'
        }
        response = self._post_edit_data(self.__class__.TEST_LEAD_ID, lead_data, api_client, admin_api_key)
        assert response.status_code == 200, response.json
        self._check_if_data_in_dict_match(lead_data, response.json)

    @db_session
    def test_edit_lead_data(self, api_client, admin_api_key):
        lead_data = {
            'name': 'Example',
            'surname': 'EditLeadModified',
            'village': Village.select().first().not_empty_code,
            'generator': 1,
            'status': 22,
            'status_comment': 'Its a SUPER good lead!',
            'generation_date': '2018-12-13T14:32:22Z',
            'next_contact': '2018-12-18T14:32:22Z',
            'reasons_for_not_buying': [112, 114],
            'home': True,
            'business': False,
            'gender': 'Female',
            'birthdate': '1991-02-21T15:32:22Z',
            'gps_longitude': 1.4,
            'gps_latitude': 1.6,
            'phone_numbers': ['+2341112223339'],
            'preferred_phone_number': '+2341112223339',
            "promised_to_pay_date": "2019-01-08T00:00:00Z",
            "planned_delivery_date": "2019-01-10T00:00:00Z",
            "commission": 1234,
            "commission_note": "Regular comission",
            "portfolio": 1,
            "sms_language": "FR",
            "verbal_language": "Pirate English"
        }
        response = self._post_edit_data(self.__class__.TEST_LEAD_ID, lead_data, api_client, admin_api_key)
        assert response.status_code == 200
        expected_data = lead_data
        expected_data.update({'status': 'Discarded'})
        expected_data.update({'reasons_for_not_buying':
                                  ['Not sure about the value of the product', 'Waiting for harvest']})
        self._check_if_data_in_dict_match(expected_data, response.json)

    def test_edit_lead_data_text(self, api_client, admin_api_key):
        lead_data = {
            'status': 'Discarded',
            'reasons_for_not_buying': ['Not sure about the value of the product', 'Waiting for harvest'],
        }
        response = self._post_edit_data(self.__class__.TEST_LEAD_ID, lead_data, api_client, admin_api_key)
        assert response.status_code == 200
        self._check_if_data_in_dict_match(lead_data, response.json)

    @db_session
    def test_approve_incomplete_lead(self, api_client, admin_api_key):
        lead_data = {
            'status': LeadStatus.get_first(StatusCategory.awaiting_decision).id
        }
        response = self._post_edit_data(self.__class__.TEST_LEAD_ID, lead_data, api_client, admin_api_key)
        lead_data = {
            'status': LeadStatus.get_first(StatusCategory.awaiting_payment).id
        }
        response = self._post_edit_data(self.__class__.TEST_LEAD_ID, lead_data, api_client, admin_api_key)
        assert response.status_code == 400
        assert response.json['error'] == 'STATUS_NOT_ALLOWED'

    def test_edit_lead_add_offer_invalid_id(self, api_client, admin_api_key):
        lead_data = {
            'offer': -1
        }
        response = self._post_edit_data(self.__class__.TEST_LEAD_ID, lead_data, api_client, admin_api_key)
        assert response.status_code == 400
        assert response.json['error'] == 'OBJECT_NOT_FOUND'

    def test_edit_lead_add_offer_valid_id(self, api_client, admin_api_key):
        lead_data = {
            'offer': 888 # This is from the Database seeder
        }
        response = self._post_edit_data(self.__class__.TEST_LEAD_ID, lead_data, api_client, admin_api_key)
        assert response.status_code == 200
        self._check_if_data_in_dict_match(lead_data, response.json)

    @db_session
    def test_edit_lead_auto_put_for_approval(self, api_client, admin_api_key):
            lead_data = {
                'status': LeadStatus.get_first(StatusCategory.awaiting_information).id
            }
            lead = Lead.get(id=self.__class__.TEST_LEAD_ID)
            response = self._post_edit_data(self.__class__.TEST_LEAD_ID, lead_data, api_client, admin_api_key)
            assert response.status_code == 200
            self._check_if_data_in_dict_match({'status': LeadStatus.get_first(StatusCategory.awaiting_decision).name}, response.json) # Should auto-change

    @db_session
    def test_approve_complete_lead(self, api_client, admin_api_key):
        lead_data = {
            'status': LeadStatus.get_first(StatusCategory.awaiting_decision).id
        }
        response = self._post_edit_data(self.__class__.TEST_LEAD_ID, lead_data, api_client, admin_api_key)
        lead_data = {
            'status': LeadStatus.get_first(StatusCategory.awaiting_payment).id # This should now be possible after adding an offer
        }
        response = self._post_edit_data(self.__class__.TEST_LEAD_ID, lead_data, api_client, admin_api_key)
        assert response.status_code == 200
        self._check_if_data_in_dict_match({'status': 'Awaiting Payment'}, response.json)

    def test_refund_unpaid_lead(self, api_client, admin_api_key):
        lead_data = {
            'payment_reference': 'REFUND_DEPOSIT'
        }
        response = self._post_edit_data(self.__class__.TEST_LEAD_ID, lead_data, api_client, admin_api_key)
        assert response.status_code == 400
        assert response.json['error'] == 'PAYMENT_WAS_DELETED', response.json

    def test_pay_deposit_invalid_reference(self, api_client, admin_api_key):
        lead_data = {
            'payment_reference': 'XXXXAAAA7777'
        }
        response = self._post_edit_data(self.__class__.TEST_LEAD_ID, lead_data, api_client, admin_api_key)
        assert response.status_code == 400
        assert response.json['error'] == 'OBJECT_NOT_FOUND'

    def test_pay_deposit_valid_reference_low_balance(self, api_client, admin_api_key):
        lead_data = {
            'payment_reference': 'TEST_PAYMENT_REFERENCE_1'
        }
        response = self._post_edit_data(self.__class__.TEST_LEAD_ID, lead_data, api_client, admin_api_key)
        assert response.status_code == 200
        with db_session:
            assert not Lead.get(id=self.__class__.TEST_LEAD_ID).deposit_paid
            payment = Lead.get(id=self.__class__.TEST_LEAD_ID).reconciled_payments.select().first().linked_payment
            assert payment.Reference == lead_data['payment_reference']

    def test_pay_deposit_valid_reference(self, api_client, admin_api_key):
        lead_data = {
            'payment_reference': 'TEST_PAYMENT_REFERENCE_2'
        }
        response = self._post_edit_data(self.__class__.TEST_LEAD_ID, lead_data, api_client, admin_api_key)
        assert response.status_code == 200
        with db_session:
            lead = Lead.get(id=self.__class__.TEST_LEAD_ID)
            assert lead.deposit_paid
            reconciled_payments = Lead.get(id=self.__class__.TEST_LEAD_ID).reconciled_payments
            assert reconciled_payments.select()[:][-1].linked_payment
            assert lead.already_paid == 150000

    def test_pay_deposit_with_cash(self, api_client, admin_api_key):
        lead_data = {'payment_reference': 'REFUND_DEPOSIT'}
        response = self._post_edit_data(self.__class__.TEST_LEAD_ID, lead_data, api_client, admin_api_key)
        assert response.status_code == 200
        lead_data = {'payment_reference': 'CASH_COLLECTED', 'amount': 100000+1000}
        response = self._post_edit_data(self.__class__.TEST_LEAD_ID, lead_data, api_client, admin_api_key)
        assert response.status_code == 200
        with db_session:
            lead = Lead.get(id=self.__class__.TEST_LEAD_ID)
            assert lead.deposit_paid
            reconciled_payments = Lead.get(id=self.__class__.TEST_LEAD_ID).reconciled_payments
            assert reconciled_payments.select()[:][-1].linked_payment
            assert lead.already_paid == 101000

    def test_edit_lead_change_offer_edited_lead(self, api_client, admin_api_key):
        lead_data = {
            'offer': 889 # This is from the Database seeder
        }
        response = self._post_edit_data(self.__class__.TEST_LEAD_ID, lead_data, api_client, admin_api_key)
        assert response.status_code == 400
        assert response.json['error'] == 'EDIT_LEAD_AWAITING_DELIVERY_NOT_ALLOWED'

    def test_edit_delivery_date(self, api_client, admin_api_key):
        lead_data = {
            'promised_to_pay_date': '2018-12-21T14:32:22Z',
            'planned_delivery_date': '2018-12-22T14:32:22Z'
        }
        response = self._post_edit_data(self.__class__.TEST_LEAD_ID, lead_data, api_client, admin_api_key)
        assert response.status_code == 200
        self._check_if_data_in_dict_match(lead_data, response.json)

    def test_refund_deposit(self, api_client, admin_api_key):
        lead_data = {
            'payment_reference': 'REFUND_DEPOSIT'
        }
        response = self._post_edit_data(self.__class__.TEST_LEAD_ID, lead_data, api_client, admin_api_key)
        assert response.status_code == 200
        self._check_if_data_in_dict_match({'status': 'Awaiting Payment'}, response.json)

    def test_change_status_after_refund(self, api_client, admin_api_key):
        lead_data = {
            'status': 'Discarded'
        }
        response = self._post_edit_data(self.__class__.TEST_LEAD_ID, lead_data, api_client, admin_api_key)
        with db_session:
            lead = Lead.get(id=self.__class__.TEST_LEAD_ID)
        assert response.status_code == 200
        self._check_if_data_in_dict_match(lead_data, response.json)

    @db_session
    def test_automatically_approve_offers(self, api_client, admin_api_key):
        lead_data = {
            'status': LeadStatus.get_first(StatusCategory.awaiting_information).id, # This should lead to the lead being auto await approval
            'offer': 889 # This offer has auto-approval on
        }
        response = self._post_edit_data(self.__class__.TEST_LEAD_ID, lead_data, api_client, admin_api_key)
        assert response.status_code == 200
        self._check_if_data_in_dict_match({'status': LeadStatus.get_first(StatusCategory.awaiting_payment).name, 'offer': 889}, response.json)
