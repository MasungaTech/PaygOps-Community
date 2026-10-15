
from core_system.client.services.client_getter_service import ClientGetterService
from core_system.client.services.client_merger_service import ClientMergerService
from flask import flash, redirect, request, render_template
from flask.helpers import url_for
from flask_login import current_user, login_required
from pony.orm import db_session
from shared.helpers.authorizer import authorizer
from shared.helpers.select2 import render
from shared.services.settings_service import SettingsService

from . import client


@db_session(retry=2)
@client.route("/<int:client_id>/merge", methods=["GET"])
@login_required
@authorizer("MergeClients")
@db_session(retry=2)
def merge_client(client_id):
    original_client = ClientGetterService.get_from_user_and_id(current_user, client_id, strict=True, main_resource=True)
    clients_list = ClientGetterService.get_list(current_user).filter(lambda c: c != original_client)
    custom_id_enabled = SettingsService.get_setting("CustomIdEnabled")
    select2 = {
        "target_client_id": {
            "items": clients_list,
            "text": "full_name_and_custom_id" if custom_id_enabled else "full_name_and_id",
            'person_search_field': True
        },
    }
    return render(
        "merge_clients.html", select2=select2, original_client=original_client
    )


@client.route("/merge-preview/<int:original_client_id>/<int:selected_client_id>", methods=['GET'])
@login_required
@db_session
def merge_preview(original_client_id, selected_client_id):
    original_client = ClientGetterService.get_from_user_and_id(current_user, original_client_id, strict=True, main_resource=True)
    selected_client = ClientGetterService.get_from_user_and_id(current_user, selected_client_id, strict=True, main_resource=True)
    selected_client_numbers = selected_client.person.phoneNumbers
    original_client_numbers = original_client.person.phoneNumbers
    phone_numbers = list(set(original_client_numbers+selected_client_numbers))
    
    return render_template(
        "preview_merged_clients.html",
        original_client=original_client,
        selected_client=selected_client,
        phone_numbers=phone_numbers
    )