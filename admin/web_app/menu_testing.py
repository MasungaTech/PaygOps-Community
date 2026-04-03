from flask_login import login_required, current_user
from flask import request, render_template, flash, get_flashed_messages, jsonify, redirect, url_for, make_response
from pony.orm import db_session, commit, select
from . import administration
from shared.helpers.authorizer import authorizer
import config


@administration.route('/test_menu', methods=['GET'])
@login_required
@authorizer('SuperAdmin')
@db_session
def menu_testing():
    return render_template('test_menu.html')


@administration.route('/test_menu/<string:action>', methods=['GET', 'POST'])
@login_required
@authorizer('SuperAdmin')
@db_session
def secret_route(action):
    if action == 'create_test_survey':
        from survey_system.system_surveys.create_system_surveys import create_all_test_surveys
        create_all_test_surveys()
        flash('Test Survey Created')
    elif action == 'upload_translation':
        main_translation = request.files.get('translation')
        if main_translation:
            lng = main_translation.filename[:2]
            main_translation.save(config.TRANSLATION_FOLDER+'/'+lng+'/'+main_translation.filename)
            from shared.services.translation_service import TRANSLATION_CACHE
            TRANSLATION_CACHE[lng] = {}
            flash('Translation Uploaded')
        else:
            flash('No translation found')
    elif action == 'download_translation':
        import os, io, zipfile
        fileobj = io.BytesIO()
        with zipfile.ZipFile(fileobj, 'w', zipfile.ZIP_LZMA) as zipf:
            for root, dirs, files in os.walk(config.TRANSLATION_FOLDER):
                for file in files:
                    path = os.path.join(root, file)
                    filename = os.path.basename(path)
                    prefix = ''
                    if not 'keys' in filename:
                        prefix = filename[:2]+'/'
                    zipf.write(path, prefix+filename)
            fileobj.seek(0)
            response = make_response(fileobj.read())
            response.headers.set('Content-Type', 'zip')
            response.headers.set('Content-Disposition', 'attachment', filename='translation.lz')
            return response
    elif action == 'generate_test_exception':
        a = '1234'
        b = 5678
        raise Exception('This is a test exception')
    elif action == 'generate_test_feature_flag_users':
        # Reference the feature flags config and name mapping
        from constants import FEATURE_FLAGS_CONFIG, FEATURE_NAME_MAP
        from core_system.role.migrations.install_permissions import create_role_in_db
        from core_system.users.services.edit_user_service import EditUserService
        from shared.helpers.auth_helper import encode_password
        from core_system.role.methods.getters import get_role_from_name
        from core_system.users.models.user_model import User

    
        for feature_code, permissions in FEATURE_FLAGS_CONFIG.items():
            if permissions: 
                # Get friendly name from mapping, fallback to feature code if not mapped
                role_name = FEATURE_NAME_MAP.get(feature_code, feature_code)
            
                # Create a new role with the feature's permissions, this will also update if it exists
                create_role_in_db(
                    role_name=f"{role_name} Tester",
                    permission_list=permissions+['ViewAPIDocumentation'],
                    type=4,  # Using type 4 for API users,
                    overwrite=True
                )
                
                # Create a test user with this role
                username = f"{feature_code.lower()}_tester@paygops.com"
                user = User.select(lambda u: u.username == username).first()
                if not user:
                    EditUserService.add_user(
                        current_user,  # No acting user needed
                        name=role_name,
                        surname="Tester",
                        username=username,
                        password=encode_password("middle.average.spin.thou"),
                        role=get_role_from_name(f"{role_name} Tester"),
                        hub=1, 
                        api_access_only=True
                    )
                else:
                    user.role = get_role_from_name(f"{role_name} Tester")
                    user.api_access_only = True
        flash('Created users')
    else:
        flash('Action not found')
    return redirect(url_for('admin.menu_testing'))