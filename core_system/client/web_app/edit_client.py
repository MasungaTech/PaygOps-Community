from core_system.operational_entities.services.client_group_getter_service import ClientGroupGetterService
from core_system.client.services.client_tag_getter import ClientTagService
from flask_login import login_required, current_user
from pony.orm import db_session
from flask import render_template, flash, redirect, url_for
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from shared.helpers.authorizer import authorizer
from core_system.client.web_app import client
from shared.services.settings_service import SettingsService
from core_system.client.services.client_getter_service import ClientGetterService
from shared.helpers.select2 import render


@client.route('/<int:client_id>/edit', methods=['GET'])
@login_required
@authorizer('EditClients', '.list_client')
@db_session
def edit_client(client_id):
    selected_client = ClientGetterService.get_from_user_and_id(current_user, client_id)
    if not selected_client:
        flash('Client does not exist or you do not have the permission to see it. ')
        return redirect(url_for('client.list_client'))

    client_groups = ClientGroupGetterService.get_list(current_user)
    villages = OperationalEntitiesGetterService.get_list(current_user, level=0).order_by(lambda V: V.name)

    select2 = {
        'client_groups': {
            'items': client_groups,
            'selected': (selected_client.person.client_group.id, selected_client.person.client_group.name) if selected_client.person.client_group else (),
            'text': 'name'
        },
        'villages': {
            'items': villages,
            'selected': (selected_client.person.village.id, selected_client.person.village.name),
            'text': 'name'
        }
    }

    return render('edit_client.html',
                    select2=select2,
                    Client=selected_client,
                    person=selected_client.person,
                    villages=villages,
                    phone_extension=SettingsService.get_setting('PhoneExtension'),
                    phone_length=SettingsService.get_setting('PhoneLength'),
                    existing_tags=ClientTagService.get_list(current_user),
                    tags=[t.id for t in selected_client.tags],
                    client_groups=client_groups)
