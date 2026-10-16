"""
direct_request.py: Contains view allowing to get text and simulate an SMS Sent, gather the answer and show it.
"""
from datetime import datetime
from shared.helpers.authorizer import authorizer
from flask import render_template, request, flash, \
    get_flashed_messages
from flask_login import login_required, current_user
from pony.orm import db_session
from config import API_PORT, API_ROUTE
from . import mentor_request
from shared.api_helpers.client_helpers.api_helper_object import APIHelper
from shared.api_helpers.client_helpers.api_exceptions import APIResourcePermissionError


@mentor_request.route('/direct_request', methods=['GET', 'POST'])
@login_required
@authorizer('AddIncomingMessages')
@db_session
def direct_request():
    if request.method == 'POST':
        message_body = request.form['body']

        if message_body:
            date = datetime.fromordinal(datetime.now().toordinal())
            epoch = datetime.fromordinal(datetime.fromtimestamp(0).toordinal())

            timedelta = date - epoch
            seconds = (timedelta.microseconds * 1e6) + timedelta.seconds + (timedelta.days * 86400)
            timestamp = int(abs(seconds))

            user_name = current_user.full_name

            sender_name = 'Web Access: ' + user_name + ' #' + str(current_user.id)

            message_data = {
                'from_number': sender_name,
                'to_number': 'Web Access',
                'body': message_body,
                'reception_datetime': datetime.now(),
                'sent_datetime': datetime.now()
            }

            api_base_url = "http://{api_route}:{api_port}/api/v1/"\
                .format(api_route=API_ROUTE, api_port=API_PORT)
            api_key = current_user.get_api_key()
            payg_api = APIHelper(api_base_url, api_key)
            try:
                success_response = payg_api.post('messages', data=message_data)
                sms_response = payg_api.get('messages/web_answers', params={'sender_number': sender_name})
            except APIResourcePermissionError:
                sms_response = ['You do not have the proper permission to send messages']
            except Exception as error:
                sms_response = ['Error: ' + str(error)]

            # TODO: Get directly on the one for the web
            try:
                for Message in sms_response:
                    flash('Answer: ' + Message)
            except:
                flash('No answer received')
        else:
            flash('Answer: The request message was empty. Please try again.')

    return render_template('manual_request.html', Message=get_flashed_messages())
