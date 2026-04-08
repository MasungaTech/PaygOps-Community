from messages_system.services.send_sms import SMSSend


class TestSendMessage:
    def test_send_messages_returns_0(self):
        sms_sender = SMSSend
        assert 0 == sms_sender.SendMessage('', 'Testing Empty')
        assert 0 == sms_sender.SendMessage(None, 'Testing None')
