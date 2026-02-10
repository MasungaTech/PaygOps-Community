from flask_login import current_user, login_required
from flask import render_template, request, abort, jsonify, url_for
from pony.orm import db_session
from constants import CUSTOMISABLE_MSGS_INFO
from messages_system.services.custom_message_getter_service import CustomMessageGetterService
from messages_system.services.message_service import MessageService
from shared.helpers.authorizer import authorizer
from shared.services.language_service import LanguageService
from shared.services.settings_service import SettingsService
from config import CUSTOMISABLE_MSGS_SECTIONS, SMS_EDITOR_CATEGORY_NAMES, SMS_VARIABLES_INFO
from . import message


@message.route('/custom_messages', methods=['GET'])
@login_required
@authorizer('EditCustomSMSAdmin')
@db_session
def custom_messages_list(): 

    return render_template(
        'list_custom_message.html',
        get_example=MessageService.get_example,
        language=request.args.get('language', SettingsService.get_setting('DefaultSMSClientsLanguage')),
        views={k: ('', v) for k,v in LanguageService.get_client_sms_language_dict().items()}
    )


@message.route('/custom_messages/<key>/edit', methods=['GET', 'POST'])
@login_required
@authorizer('EditCustomSMSAdmin')
@db_session
def edit_custom_message(key):

    if not MessageService.valid_custom_key(key):
        abort(404)

    if request.method == 'POST':
        try:
            if request.json.get('default', False):
                MessageService.remove_custom_message(key, request.json['lang'])
            elif request.json.get('disabled', False):
                MessageService.set_custom_message(key,
                                                  '',
                                                  request.json['lang'])
            else:
                MessageService.set_custom_message(key,
                                                  request.json['template'],
                                                  request.json['lang'])
        except KeyError as error:
            return str(error), 400
        except Exception as error:
            return str(error), 500
        return jsonify({'success': True}), 200

    class o:
        def get_link(self):
            return url_for('message.edit_custom_message', key=key)
        
        def get_display_id(self):
            return CUSTOMISABLE_MSGS_INFO[key]['name']
        
    return render_template(
        'edit_custom_message.html',
        key=key,
        sms_variables_info=SMS_VARIABLES_INFO,
        get_template=MessageService.get_template,
        get_default=MessageService.get_default_template,
        get_msg=lambda lang: CustomMessageGetterService.get_from_user_and_properties(current_user, key=key, language=lang),
        is_disabled=MessageService.is_disabled,
        object=o()
    )
