from flask_login import login_required, current_user
from flask import redirect, request, url_for, flash, render_template
from pony.orm import db_session

from shared.helpers.authorizer import authorizer
from config import API_PORT, API_ROUTE
from shared.api_helpers.client_helpers.api_helper_object import APIHelper
from shared.api_helpers.client_helpers.api_exceptions import APIResourcePermissionError

from datetime import datetime
import json, config, os

from . import message


@message.route('/add', methods=['GET'])
@login_required
@authorizer('AddIncomingMessages')
@db_session
def add_message_manually_view():
    return render_template('add_manual_message.html')


@message.route('/add', methods=['POST'])
@login_required
@authorizer('AddIncomingMessages')
@db_session
def add_message_manually():

    body = request.form.get('body', None)
    from_number = request.form.get('from_number', None)
    now = datetime.now()

    if body and from_number:
        message_data = {
            'from_number': from_number,
            'to_number': 'Manually Added',
            'body': body,
            'reception_datetime': now,
            'sent_datetime': now
        }

        api_base_url = "http://{api_route}:{api_port}/api/v1/" \
            .format(api_route=API_ROUTE, api_port=API_PORT)
        api_key = current_user.get_api_key()
        payg_api = APIHelper(api_base_url, api_key)

        # We log the attempt
        manual_message_log = {
            'user_name': current_user.full_name,
            'user_id': current_user.id,
            'user_agent': str(request.user_agent),
            'time': str(now),
            'from_number': str(from_number),
            'body': body,
            'user_ip': str(request.environ.get('HTTP_X_REAL_IP', request.remote_addr))
        }

        try:
            # We write the log
            file = open(config.MANUAL_MESSAGE_LOG_PATH, 'a')
            file.write(json.dumps(manual_message_log) + '\n')

            success_response = payg_api.post('messages', data=message_data)
            sms_response = payg_api.get('messages/web_answers', params={'sender_number': from_number})
        except APIResourcePermissionError:
            sms_response = ['You do not have the proper permission to send messages']
        except Exception as error:
            sms_response = ['Error: ' + str(error)]

        return render_template('add_manual_message.html', answers=sms_response)

    else:
        flash('Information incomplete! Please try again with full information.')
        return render_template('manual_message_form.html')


@message.route('/manual_list')
@login_required
@authorizer('AddIncomingMessages')
@db_session
def manual_message_list():

    manual_message_logs = list(reversed(list(open(config.MANUAL_MESSAGE_LOG_PATH, 'r')))) \
        if os.path.exists(config.MANUAL_MESSAGE_LOG_PATH) else []

    return render_template('manual_message_list.html',
                           manual_message_logs=manual_message_logs,
                           json=json)
