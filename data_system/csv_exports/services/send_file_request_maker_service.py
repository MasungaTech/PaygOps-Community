import gc
import os
from datetime import datetime, timedelta
from urllib.parse import urlencode

import config
from constants import DATA_EXPORTS_CONFIG
from core_system.users.models.user_model import User
from flask import flash, make_response, redirect, request, url_for
from data_system.csv_exports.services.csv_export_service import CSVExportService
from data_system.csv_exports.services.custom_forms_export_service import CustomFormsExportService

from pony import orm
from shared.api_helpers.server_helpers.jwt_generation import generate_jwt
from shared.cache.redis_config import get_cache_key, set_cache_key
from shared.logger.loggers import LogService
from shared.services.celery_queue_service import CeleryQueueService
from shared.services.email_sender import EmailSender


class SendFileRequestMaker:

    GENERATOR_FUNCTION_MAP = {key: data['model'] for key, data in DATA_EXPORTS_CONFIG.items()}
    TEMP_DIR = os.path.join(config.TEMP_PATH, 'csv_exports')

    NOT_STATIC_CACHED = [
        'custom_forms_data',
    ]

    @classmethod
    def send(cls, file, user=None):
        data_file = cls._get_or_generate(file, user=user)
        output = make_response(data_file)
        return cls._add_headers(output, file)

    @classmethod
    def _add_headers(cls, response, filename):
        content_disp = 'attachment; filename='+filename+'_'+datetime.now().strftime('%Y%m%d%H%M%S')+'.csv'
        response.headers["Content-Disposition"] = content_disp
        response.headers["Content-type"] = "text/csv"
        return response

    @classmethod
    def _get_or_generate(cls, export_name, user=None):
        email_user_id = request.args.get('email_user_id')
        dynamic = export_name in cls.NOT_STATIC_CACHED
        if dynamic and not email_user_id:
            return cls._generate(export_name, data=request.args)
        
        data = request.args
        cache_name = cls.get_cache_name(export_name, data)
        cache_value = get_cache_key(cache_name)
        
        if not cache_value or request.args.get('nocache', False):
            if dynamic or request.args.get('nocache', False):
                from worker_app.tasks.compute_csv_exports import compute_csv_data_now
                if not email_user_id and user and not user.is_anonymous:
                    email_user_id = user.id
                if email_user_id:
                    CeleryQueueService.execute_task(compute_csv_data_now, tasks=[export_name], data=data, email_user_id=email_user_id)
                    flash('The data files are now being computed. You will receive them by email soon.')
                else:
                    CeleryQueueService.execute_task(compute_csv_data_now, tasks=[export_name])
                    flash('The data files are now being computed. Please check later.')
            else:
                flash('The data files are still being computed. Please check later.')
            return redirect(url_for('admin.data_exports'))
        
        # Read the file from disk
        file_content = cls._get_file_content(export_name, data)
        if file_content:
            return file_content
        return redirect(url_for('admin.data_exports'))

    @classmethod
    def _get_file_content(cls, export_name, data={}):
        # Read the file from disk
        file_path = cls._get_file_path(export_name, data)
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                return f.read()
        return None

    @classmethod
    def _generate(cls, export_name, data={}):
        model = cls.GENERATOR_FUNCTION_MAP[export_name]
        if export_name == 'custom_forms_data':
            # This has it's own service inherited from the other to do filtering
            export_service = CustomFormsExportService(model)
        else:
            export_service = CSVExportService(model)
        
        # Ensure temp directory exists
        os.makedirs(cls.TEMP_DIR, exist_ok=True)
        
        # Generate CSV and write to file
        file_path = cls._get_file_path(export_name, data)
        export_service.get_simple_export(data, file_path=file_path)
        
        # Set cache flag
        cache_name = cls.get_cache_name(export_name, data)
        if export_name in cls.NOT_STATIC_CACHED:
            set_cache_key(cache_name, "generated", cls.seconds_until_end_of_day() + 3600 * 2)
            return cls._get_file_content(export_name, data)
        else:
            set_cache_key(cache_name, "generated", 3600 * 30)

    @classmethod
    def _get_file_path(cls, export_name, data=None):
        cache_name = cls.get_cache_name(export_name, data)
        filename = f"{cache_name}.csv"
        return os.path.join(cls.TEMP_DIR, filename)

    @classmethod
    def prepare_export_cache(cls, tasks=None, data={}):
        for key in cls.GENERATOR_FUNCTION_MAP:
            if not key in cls.NOT_STATIC_CACHED and (not tasks or key in tasks):
                with orm.db_session(strict=True):
                    print('Computing '+str(key)+'...')
                    cls._generate(key, data=data)
                    orm.rollback()  # We do that to free any remaining memory
                gc.collect()

    @classmethod
    def email_export(cls, tasks, email_user_id, data={}):
        for key in cls.GENERATOR_FUNCTION_MAP:
            if key in tasks:
                with orm.db_session(strict=True):
                    print('Computing '+str(key)+'...')
                    file = cls._generate(key, data=data)
                    orm.rollback() # We do that to free the memory
                    cls._send_export_email(email_user_id, key, data=data)
    
    @classmethod
    @orm.db_session
    def _send_export_email(cls, email_user_id, export_name, data={}):
        try:
            this_user = User.get(id=email_user_id)
            export_url = cls._generate_export_link(this_user, export_name, data=data)
            content = f'''
                Hello {this_user.full_name}, <br><br>
                Please find the data export you requested <a href="{export_url}">here</a>. <br><br>
                The link will be valid for 24h. <br><br>
                Kind regards,<br>The PaygOps Team
            '''
            email = EmailSender(
                this_user.full_name,
                this_user.email,
                'PaygOps Data Export Ready',
                body=content,
                html=True
            )
            email.send()
        except Exception as e:
            LogService.FatalNoRequest(e)

    @classmethod
    def _generate_export_link(cls, user, export_name, data={}):
        expiration = datetime.now()+timedelta(days=1)
        key = generate_jwt(user.id, ['ExportDataAdmin'], 'Solaris Offgrid', config.api_secret, expiration)
        base_url = config.PAYG_API_URL + f'/file/exports/{export_name}_static'
        data['key'] = key
        url = base_url + '?' + urlencode(data)
        return url

    @classmethod
    def get_cache_name(cls, export_name, data=None):
        if export_name in cls.NOT_STATIC_CACHED:
            clean_data = dict(data.copy())
            clean_data.pop('key', None)
            clean_data.pop('email_user_id', None)
            return export_name+'_'+str(clean_data)
        return export_name

    @classmethod
    def seconds_until_end_of_day(cls):
        dt = datetime.now()
        return ((24 - dt.hour - 1) * 60 * 60) + ((60 - dt.minute - 1) * 60) + (60 - dt.second)
