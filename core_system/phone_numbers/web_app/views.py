from pony.orm.core import rollback
from core_system.phone_numbers.services.phone_number_getter import PhoneNumberGetterService
from pony.orm import db_session, commit
from flask import render_template, request, abort, \
    redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from shared.helpers.authorizer import authorizer
from core_system.person.models.person_model import Person
from shared.helpers.pagination import Pagination
from shared.logger.loggers import Error
from . import phone_numbers
from core_system.phone_numbers.model import PhoneNumbers
from core_system.phone_numbers.helpers import save_phone_number, get_owner_data_if_exists, get_owned_phone_number_message, \
    remove_number, set_as_preferred, add_number
from shared.services.settings_service import SettingsService
import json


@phone_numbers.route('/')
@login_required
@authorizer('ViewPhoneNumbers')
@db_session
def search_phone_numbers():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', Pagination.PER_PAGE))
    sort = request.args.get('sort', 'name:asc')
    search = request.args.get('search', '').lower()
    numbers = PhoneNumbers.select(number='-1')

    # We only show results if search
    if search:
        # We use this on purpose as access to pages is already restricted
        numbers = PhoneNumbers.select()
        search = search.replace('+','').replace(' ', '')
        numbers = numbers.filter(
            lambda n: search in n.number
        ).order_by(lambda n: n.person.full_name)

    pagination = Pagination(page,
                            per_page,
                            numbers,
                            sort,
                            search=search)
    return render_template('search.html', pagination=pagination)


@phone_numbers.route('/<int:p_id>/edit', methods=['POST'])
@login_required
@authorizer('EditPhoneNumbers')
@db_session
def update(p_id):
    new_owner = request.form.get('persons', None)
    if new_owner:
        res, string = save_phone_number(p_id, int(new_owner))
        flash(string)
        commit()
    return redirect(url_for('.view', p_id=p_id))


@phone_numbers.route('/<number>/exists', methods=['GET'])
@login_required
@authorizer('ViewPhoneNumbers')
@db_session
def exists(number):
    owner = get_owner_data_if_exists(number)
    if owner:
        if SettingsService.get_setting('AllowMultiplePersonsWithSamePhoneNumber'):
            return jsonify({'exists': False})
        else:
            return jsonify({'exists': True, 'message': get_owned_phone_number_message(owner)})
    else:
        return jsonify({'exists': False})


@phone_numbers.route('/<number>/<int:person_id>/remove', methods=['GET'])
@login_required
@authorizer('DeletePhoneNumbers')
@db_session
def remove(number, person_id):
    try:
        person = Person.get(id=person_id)
        if not person: raise Error('Person not found')
        remove_number(number, current_user, person)
    except Error as e:
        rollback()
        return jsonify({'message': e.description, 'code': e.code, 'success': False})
    else:
        commit()
        return jsonify({'success': True, 'message': f'The phone number has been removed from this owner. '})


@phone_numbers.route('/<number>/<int:person_id>/preferred', methods=['GET'])
@login_required
@authorizer('EditPhoneNumbers')
@db_session
def set_preferred(number, person_id):
    if set_as_preferred(number, person_id):
        commit()
        return jsonify({'message': 'The phone number has been set as the preferred contact phone number'})
    else:
        return jsonify({'message': 'The phone number could NOT be set as contact phone, '
                                   'if you are creating a new lead, this is normal, '
                                   'it will be set automatically on save'})


@phone_numbers.route('/add_new', methods=['POST'])
@login_required
@authorizer('EditPhoneNumbers')
@db_session
def add_new_number():
    data = json.loads(request.form['data'])
    this_number = data['number']
    lead = data.get('lead_id')
    this_person = Person.get(id=data['person_id'])
    result = add_number(this_number, this_person, current_user, lead)
    return jsonify(**result)
