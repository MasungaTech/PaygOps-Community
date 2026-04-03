from datetime import datetime
import pytest
from pony.orm import db_session
from mock import patch
from shared.helpers.client_creator import ClientCreator
from messages_system.services.client_sms_handler import handle_client_SMS


class TestClientSmsHandler:
    
    @pytest.fixture(autouse=True)
    @db_session
    def setup_method(self, api_client, good_api_key):
        self.client = ClientCreator.create(api_client, good_api_key)
        self.phone_number = '123456789'
        self.reception_time = datetime.now()

    @db_session
    @patch('messages_system.services.client_sms_handler.handle_activation_request',
           return_value={
                'success': True,
                'status': 'ACTIVATION_REQUEST_SUCCESS',
                'activation_answer_code': 'FOOOOO',
                'expiration_time_day': datetime.now().strftime('%d'),
                'expiration_time_month': datetime.now().strftime('%m'),
                'expiration_time_year': datetime.now().strftime('%Y'),
           })
    def test_valid_command(self, *args):
        command = 'FOO_BAR'
        resp = handle_client_SMS(self.client, self.phone_number, command, self.reception_time)
        args[0].assert_called_with(self.client, command)
        assert resp == 1

    @db_session
    @pytest.mark.parametrize("test_input, result", [
        ('#', 1),
        ('FOO#BAR', 1),
        ('####', 1)
    ])
    def test_invalid_command(self, test_input, result):
        with patch('messages_system.services.client_sms_handler.handle_activation_request') as mock_fn:

            resp = handle_client_SMS(self.client, self.phone_number, test_input, self.reception_time)
            mock_fn.assert_not_called()
        assert resp == result
