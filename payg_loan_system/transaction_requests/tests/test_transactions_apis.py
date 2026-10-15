from uuid import uuid1
import json
from pony.orm import db_session
from shared.helpers.client_creator import ClientCreator
from config import API_PREFIX
from shared.services.settings_service import SettingsService


class TestTransactionsAPIs:

    def test_collect_cash_transaction_resource_and_sync_works(self, api_client, admin_api_key, super_admin_user):

        with db_session:
            client = ClientCreator.create(api_client, admin_api_key)
            print(client.person.village.parent.parent.name)
            print(super_admin_user().can_access('CollectCashActions', person=client.person))
            device = client.contracts.select().first().linked_device
            data = {
                'device_serial': device.composed_serial,
                'amount': 13,
                'note': 'test note'
            }
            data2 = {
                'contract_reference': device.contract.reference,
                'amount': 13,
                'note': 'test note'
            }
            
            data3 = {
                'device_serial': device.composed_serial,
                'client_id': client.id,
                'note': 'test note'
            }
            data4 = {
                'contract_reference': device.contract.reference,
                'client_id': client.id,
                'note': 'test note'
            }
            
            checks = {
                'success': True,
                'status': 'ACTIVATION_REQUEST_SUCCESS'
            }

        self._helper(api_client, admin_api_key, 'collect_cash', data, sms=True)
        self._helper(api_client, admin_api_key, 'collect_cash', data2, sms=True)

        self._helper(api_client, admin_api_key, 'sync_activation', data3, checks, sms=True)
        self._helper(api_client, admin_api_key, 'sync_activation', data4, checks, sms=True)

    def test_default_undo_default_transaction_resource(self, api_client, admin_api_key):

        with db_session:
            client = ClientCreator.create(api_client, admin_api_key)
            contract = client.contracts.select().first()
            ClientCreator.post_payment({
                "transaction_id": "TestTransactionPayment"+str(client.id),
                "sender_name": client.full_name,
                "sender_msisdn": client.person.contactPhone.number,
                "amount": str(contract.offer.base_price_amount)
            }, api_client, admin_api_key)
            SettingsService.set_setting('ContractDeviceRestrictions', 'require_device')
            device = contract.linked_device
            data = {'device_serial': device.composed_serial, 'note': 'test note'}
            data2 = {'contract_reference': device.contract.reference, 'note': 'test note'}

        self._helper(api_client, admin_api_key, 'default', data)
        self._helper(api_client, admin_api_key, 'undo_default', data2, sms=True)
        self._helper(api_client, admin_api_key, 'default', data2)

    def test_deregister_transaction_resource(self, api_client, admin_api_key):

        with db_session:
            client = ClientCreator.create(api_client, admin_api_key)
            contract = client.contracts.select().first()
            ClientCreator.post_payment({
                "transaction_id": "TestTransactionPayment"+str(client.id),
                "sender_name": client.full_name,
                "sender_msisdn": client.person.contactPhone.number,
                "amount": str(contract.offer.base_price_amount)
            }, api_client, admin_api_key)
            device = contract.linked_device
            data = {'device_serial': device.composed_serial, 'note': 'test note'}
            undo_data = {'contract_reference': device.contract.reference,
                         'device_serial': device.composed_serial, 'note': 'test note'}
            data2 = {'contract_reference': device.contract.reference, 'note': 'test note'}

        self._helper(api_client, admin_api_key, 'deregister', data)
        self._helper(api_client, admin_api_key, 'undo_default', undo_data, sms=True)
        self._helper(api_client, admin_api_key, 'deregister', data2)

    def test_give_delay_transaction_resource(self, api_client, admin_api_key):

        with db_session:
            client = ClientCreator.create(api_client, admin_api_key)
            device = client.contracts.select().first().linked_device
            data = {
                'device_serial': device.composed_serial,
                'delayed_days': 5,
                'note': 'TEST'
            }
            data2 = {
                'contract_reference': device.contract.reference,
                'delayed_days': 5,
                'note': 'TEST'
            }

        self._helper(api_client, admin_api_key, 'give_delay', data, sms=True)
        self._helper(api_client, admin_api_key, 'give_delay', data2, sms=True)

    def test_give_discount_transaction_resource(self, api_client, admin_api_key):

        with db_session:
            client = ClientCreator.create(api_client, admin_api_key)
            device = client.contracts.select().first().linked_device
            data = {
                'device_serial': device.composed_serial,
                'discounted_days': None,
                'discounted_amount': 5,
                'note': 'TEST'
            }
            data2 = {
                'contract_reference': device.contract.reference,
                'discounted_days': None,
                'discounted_amount': 5,
                'note': 'TEST'
            }

        self._helper(api_client, admin_api_key, 'give_discount', data, sms=True)
        self._helper(api_client, admin_api_key, 'give_discount', data2, sms=True)

    def test_registration_transaction_resource(self, api_client, admin_api_key):

        with db_session:
            lead = ClientCreator.create_lead()
            device = ClientCreator.create_device()
            ClientCreator.post_payment({
                "transaction_id": "DownpaymentTestPayment"+str(lead.id),
                "sender_name": lead.full_name,
                "sender_msisdn": lead.person.contactPhone.number,
                "amount": str(lead.offer.registration_fee+lead.offer.base_price_amount)
            }, api_client, admin_api_key)
            data = {
                'device_serial': device.composed_serial,
                'lead_id': lead.id,
                'note': 'test note'
            }

        self._helper(api_client, admin_api_key, 'registration', data, sms=True)

    def test_reverse_repayment_transaction_resource(self, api_client, admin_api_key):

        with db_session:
            client = ClientCreator.create(api_client, admin_api_key)
            ClientCreator.post_payment({
                "transaction_id": "RepaymentTestPayment"+str(client.id),
                "sender_name": client.full_name,
                "sender_msisdn": client.person.contactPhone.number,
                "amount": 10
            }, api_client, admin_api_key)
            repayment = client.contracts.select().first().repayments.select()[:][1]
            data = {'repayment_id': str(repayment.id)}

        self._helper(api_client, admin_api_key, 'reverse_repayment', data, sms=True)

    def test_swap_device_transaction_resource(self, api_client, admin_api_key):

        with db_session:
            client = ClientCreator.create(api_client, admin_api_key)
            contract = client.contracts.select().first()
            ClientCreator.post_payment({
                "transaction_id": "TestTransactionPayment"+str(client.id),
                "sender_name": client.full_name,
                "sender_msisdn": client.person.contactPhone.number,
                "amount": str(contract.offer.base_price_amount)
            }, api_client, admin_api_key)
            old_device = contract.linked_device
            new_device = ClientCreator.create_device({"serial_number": "TSWAPINGDEVICE2"})
            data = {
                'old_device_serial': old_device.composed_serial,
                'new_device_serial': new_device.composed_serial,
                'note': 'test note'
            }
            data2 = {
                'contract_reference': old_device.contract.reference,
                'new_device_serial': old_device.composed_serial,
                'note': 'test note'
            }

        self._helper(api_client, admin_api_key, 'swap_device', data, sms=True)
        self._helper(api_client, admin_api_key, 'swap_device', data2, sms=True)

    def test_sync_activation_transaction_resource_fails(self, api_client, admin_api_key):

        with db_session:
            client = ClientCreator.create(api_client, admin_api_key)
            contract = client.contracts.select().first()
            ClientCreator.post_payment({
                "transaction_id": "TestTransactionPayment"+str(client.id),
                "sender_name": client.full_name,
                "sender_msisdn": client.person.contactPhone.number,
                "amount": str(contract.offer.base_price_amount)
            }, api_client, admin_api_key)
            device = contract.linked_device
            checks = {
                'success': True,
                'status': 'ACTIVATION_REQUEST_SUCCESS'
            }
            data = {
                'device_serial': device.composed_serial,
                'client_id': client.id,
            }
            data2 = {
                'contract_reference': device.contract.reference,
                'client_id': client.id,
            }

        self._helper(api_client, admin_api_key, 'sync_activation', data, checks, sms=True)
        self._helper(api_client, admin_api_key, 'sync_activation', data2, checks, sms=True)

    @classmethod
    def _helper(cls, client, key, transaction, data, checks=None, sms=False):

        uuidstr = str(uuid1())
        url = API_PREFIX + '/transaction_requests/' + transaction + '/' + uuidstr
        headers = {'Authorization': 'Bearer '+key}

        resp = client.post(url, headers=headers, json=data)
        cls._checks(resp, checks)

        resp = client.get(url, headers=headers)
        cls._checks(resp, checks)
        
        resp = client.put(url, headers=headers, json={'sent_to_client': True})
        if transaction == 'reverse_repayment':
            assert 'has been reversed' in resp.get_json()['sent_to_client']['Body']
        elif sms and transaction not in ['reverse_repayment']:
            assert '123 456 789' in resp.get_json()['sent_to_client']['Body']
        else:
            assert resp.get_json()['error_message'] == 'The transaction answer has no messages for clients', resp.get_json()

    @staticmethod
    def _checks(response, checks):

        assert response.status_code == 200, response.get_json()

        resp_content = response.get_json()
        answer = resp_content['answer_data'][0] if isinstance(
            resp_content['answer_data'], list
        ) else resp_content['answer_data'] 

        checks = {'success': True} if not checks else checks
        for check in checks:
            assert answer[check] == checks[check]
