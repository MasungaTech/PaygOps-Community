import random
import json
from pony.orm import db_session
from tests.base_test import BaseViewTest
from config import CUSTOMISABLE_MSGS_INFO, AVAILABLE_CLIENTS_SMS_LANGUAGES
from messages_system.services.message_service import MessageService

class TestListCustomMessagesView(BaseViewTest):
    url = 'message.custom_messages_list'
    template = 'list_custom_message.html'
    
class TestEditCustomMessageView(BaseViewTest):
    url = 'message.edit_custom_message'
    template = 'edit_custom_message.html'
    params = {'key': random.choice(list(CUSTOMISABLE_MSGS_INFO))}
    lang = random.choice(list(AVAILABLE_CLIENTS_SMS_LANGUAGES))
    
    @db_session
    def test_404_unknown_custom_message_key(self, super_admin_app): 
        response = self.get(super_admin_app, params={'key': 'MADE_UP_KEY_THAT_DOESNT_EXISTS'})
        assert response.status_code == 404

    @db_session
    def test_actions_edit_custom_message_view(self, super_admin_app):
        data = {
            'default': False,
            'disabled': False,
            'template': 'TEST CUSTOM MESSAGE',
            'lang': self.lang
        }
        response = self.post(super_admin_app, data=json.dumps(data), content_type='application/json')
        assert response.status_code == 200
        assert json.loads(response.data)['success']
        assert MessageService.get_template(self.params['key'], self.lang) == data['template']
    
    @db_session
    def test_actions_default_custom_message_view(self, super_admin_app):
        data = {
            'default': True,
            'lang': self.lang
        }
        response = self.post(super_admin_app, data=json.dumps(data), content_type='application/json')
        assert response.status_code == 200
        assert json.loads(response.data)['success']
        assert MessageService.get_template(self.params['key'], self.lang) == MessageService.get_default_template(self.params['key'],self.lang)
        
    @db_session
    def test_actions_disabled_custom_message_view(self, super_admin_app):
        data = {
            'disabled': True,
            'lang': self.lang
        }
        response = self.post(super_admin_app, data=json.dumps(data), content_type='application/json')
        assert response.status_code == 200
        assert json.loads(response.data)['success']
        assert MessageService.is_disabled(self.params['key'], self.lang)
        