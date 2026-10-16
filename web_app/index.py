import os
from flask import render_template, redirect, url_for, send_from_directory, jsonify, make_response, request, flash
from flask_login import login_required, current_user, logout_user
from shared.cache.redis_config import get_key
from pony.orm import *
from web_app import app
import config
from constants import HIDE_CHROME_CHECKER_COOKIE_NAME, HIDE_CHROME_CHECKER_COOKIE_MAX_AGE
from shared.services.settings_service import SettingsService


# For testing
from payg_loan_system.devices.model.device import Device
from random import randint
from time import sleep


@app.route('/')
@db_session
@login_required
def index():
    if current_user.api_access_only is True:
        return redirect(url_for('admin.api_docs'))
    is_custom_app = config.check_if_custom_app(request)
    if is_custom_app:
        if current_user.can_access('RunUserJourney'):
            return redirect(url_for('user_journey_editor.journeys_big_menu'))
        else:
            flash('You are not authorized to access the custom app', 'error')
            return redirect(url_for('overview.welcome_overview'))
    elif current_user.can_access_in_any('ViewClients'):
        return redirect(url_for('overview.display_overview'))
    elif current_user.can_access_in_any('ViewLeads'):
        return redirect(url_for('leads.list_lead'))
    elif current_user:
        return redirect(url_for('overview.welcome_overview'))
    else:
        logout_user()
        return redirect(url_for('login.login'))


@app.route('/health')
@db_session
def health():
    return jsonify({'healthy': True})


@app.route('/db_load_test_gyM5JuAywJcv72c6')
@db_session
def db_load_test():
    rand = randint(1,500)
    if rand % 3:
        sleep(rand/1000)
    return jsonify({'count': str(select(d.composed_serial for d in Device if '33' in d.composed_serial and d.credit_balance >= 0)[:])})


@app.route('/worker/health')
@db_session
def worker_health():
    if config.ENV_VAR == 'TEST' or (get_key('beat_healthcheck') and get_key('green_healthcheck')):
        return jsonify({'healthy': True}), 200
    else:
        return jsonify({'healthy': False}), 500


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/logo')
@db_session
def logo():
    if SettingsService.get_setting('PlatformLogoPictureID') and os.path.isfile(config.CONTENT_PATH+config.LOGO_FILE_NAME):
        return send_from_directory(config.CONTENT_PATH, config.LOGO_FILE_NAME)
    else:
        return send_from_directory('./static/img/', 'paygops_bottom_logo-dark.png')


@app.route('/logo_inverted')
@db_session
def logo_inverted():
    if SettingsService.get_setting('PlatformLogoPictureID') and os.path.isfile(config.CONTENT_PATH+config.LOGO_FILE_NAME_INVERTED):
        return send_from_directory(config.CONTENT_PATH, config.LOGO_FILE_NAME_INVERTED)
    else:
        return send_from_directory('./static/img/', 'paygops_bottom_logo-light.png')





