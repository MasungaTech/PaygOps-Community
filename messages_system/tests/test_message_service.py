from pony.orm import db_session
import pytest
from mock import Mock
from messages_system.services.message_service import MessageService
from messages_system.models.custom_message import CustomMessage
from config import CUSTOMISABLE_MSGS_INFO, CUSTOMISABLE_MSGS_SECTIONS, AVAILABLE_CLIENTS_SMS_LANGUAGES


class TestMessageService:

    def test_custom_sms_info_consistent(self):
        info_keys = set(CUSTOMISABLE_MSGS_INFO.keys())
        sect_keys = set([])
        for category in CUSTOMISABLE_MSGS_SECTIONS:
            for key in CUSTOMISABLE_MSGS_SECTIONS[category]:
                for msg_inf_key in CUSTOMISABLE_MSGS_SECTIONS[category][key]:
                    sect_keys.add(msg_inf_key)
        
        assert info_keys == sect_keys

    def test_lead_approved_no_downpayment_default_templates_exist(self):
        for language in AVAILABLE_CLIENTS_SMS_LANGUAGES:
            template = MessageService.get_default_template('LEAD_APPROVED_NO_DOWNPAYMENT', language)
            assert template
            assert template != 'LEAD_APPROVED_NO_DOWNPAYMENT'
        
    @db_session
    def test_set_custom_message(self):
        MessageService.set_custom_message('PAYMENT_RECEIVED', 'TO BE OVERRIDEN', 'SW')
        MessageService.set_custom_message('PAYMENT_RECEIVED', 'blabla', 'SW')
        #also test that if custom exits, replace it
        assert CustomMessage.get(key='PAYMENT_RECEIVED', language='SW').template == 'blabla'
        assert MessageService.get_template('PAYMENT_RECEIVED', 'SW') == 'blabla'
        assert MessageService.get_message({'status': 'PAYMENT_RECEIVED', 'amount': '123'}, 'SW', for_client=True) == 'blabla'

    @db_session
    def test_custom_message_prioritization(self):
        MessageService.set_custom_message('CASH_PAYMENT_SUCCESS_CLIENT', 'blabla', 'SW')
        assert "$TEST$" in MessageService.get_message({
            'status': 'CASH_PAYMENT_SUCCESS_CLIENT',
            'amount': "$TEST$",
            'currency_sym': "",
            'name': "",
            'surname': "",
            "transaction_id": "",
            "commission": "",
            'client_id': 1
        }, 'SW') # if not forced to be for client, it is rendered for user
        assert MessageService.get_message({'status': 'PAYMENT_RECEIVED', 'amount': '123'}, 'SW', for_client=True) == 'blabla' #forced to client
        assert MessageService.get_message({'status': 'PAYMENT_RECEIVED', 'amount': '123'}, 'SW', person=Mock(client=True)) == 'blabla' #forced to client through person
        assert MessageService.get_message({'status': 'PAYMENT_RECEIVED', 'amount': '123'}, 'SW', person=Mock(lead=True)) == 'blabla' #forced to client through person


    @db_session
    def test_remove_custom_message(self):
        MessageService.remove_custom_message('PAYMENT_RECEIVED', 'SW')
        assert CustomMessage.get(key='PAYMENT_RECEIVED', language='SW') is None
        assert (MessageService.get_template('PAYMENT_RECEIVED', 'SW') ==
                MessageService.get_default_template('PAYMENT_RECEIVED', 'SW'))
        
    @db_session
    def test_disabled_custom_message(self):
        MessageService.set_custom_message('PAYMENT_RECEIVED', '', 'SW')
        assert CustomMessage.get(key='PAYMENT_RECEIVED', language='SW').template == ''
        assert MessageService.get_template('PAYMENT_RECEIVED', 'SW') == ''
        assert MessageService.is_disabled('PAYMENT_RECEIVED', 'SW')

    @db_session
    def test_user_only_registration_status_is_not_sent_to_client(self):
        status = {
            'status': 'REGISTRATION_FROM_LEAD_SUCCESS_NO_CODE_NO_DEVICE',
            'name': 'Eric',
            'surname': 'Test',
            'client_id': 17,
            'contract_reference': 'C-17',
        }
        assert MessageService.get_message(status, 'EN', for_client=True) == ''

        user_message = MessageService.get_message(status, 'EN', for_client=False)
        assert 'REGISTRATION_FROM_LEAD_SUCCESS_NO_CODE_NO_DEVICE' not in user_message
        assert 'Eric' in user_message
        assert 'C-17' in user_message

    @db_session
    def test_combined_client_sms_omits_user_only_registration_status(self):
        answer = [
            {
                'status': 'CASH_PAYMENT_SUCCESS_LEAD',
                'amount': '2000',
                'name': 'Eric',
                'surname': 'Test',
                'lead_id': 1,
                'transaction_id': 'ND-001',
                'commission': '0',
            },
            {
                'status': 'REGISTRATION_FROM_LEAD_SUCCESS_NO_CODE_NO_DEVICE',
                'name': 'Eric',
                'surname': 'Test',
                'client_id': 17,
                'contract_reference': 'C-17',
            },
        ]
        message = MessageService.get_message(answer, 'EN', for_client=True)
        assert 'REGISTRATION_FROM_LEAD_SUCCESS_NO_CODE_NO_DEVICE' not in message
        assert '2000' in message
        assert '\n' not in message

        only_registration = MessageService.get_message([answer[1]], 'EN', for_client=True)
        assert only_registration == ''

    @db_session
    def test_set_invalid_custom_message(self):
        with pytest.raises(Exception) as error:
            MessageService.set_custom_message('INSUFFICIENT_FUNDS', 'blabla', 'SW')
        assert str(error.value) == "MESSAGE_KEY_NOT_CUSTOMISABLE"
        with pytest.raises(Exception) as error:
            MessageService.set_custom_message('PAYMENT_RECEIVED', 'blabla {invalid_variable}', 'SW')
        assert (str(error.value) ==
                '"Invalid variable \'invalid_variable\' is undefined in custom message template for PAYMENT_RECEIVED in SW"')
