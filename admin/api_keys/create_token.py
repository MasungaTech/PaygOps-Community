from flask import render_template
from flask_login import login_required, current_user
from pony.orm import *
from datetime import datetime, timedelta

import config
from core_system.users.services.user_getter_service import UserGetterService

from shared.helpers.authorizer import authorizer
from . import api_system
from shared.api_helpers.server_helpers.jwt_generation import generate_jwt


@api_system.route('/create_token', methods=['GET'])
@login_required
@authorizer('CreateAPITokenAdmin')
@db_session
def create_token():
    users = UserGetterService.get_list(current_user)
    users_list = [(u.id, f'{u.full_name} (ID: {u.id})') for u in users if u.username != config.SYSTEM_EMAIL]
    return render_template('create_token.html', users_list=users_list)


