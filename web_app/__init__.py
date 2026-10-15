# THIS ABSOLUTELY NEEDS TO BE FIRST
import config

import shared.helpers.database_hook
import logging
import os

from flask import Flask
from flask_caching import Cache
from flask_login import LoginManager

from shared.helpers.log_helper import Logger
from web_app.registerer import BlueprintRegisterer
from shared.database_mapper import DatabaseMapper
from shared.helpers.https_helper import ReverseProxied
from shared.helpers.debugger import initialize_debugger
from shared.helpers.jinja_markdown import MarkdownExtension
import jinja2
from web_app.asset_builds import Environment, register_assets

initialize_debugger(5678)

app = Flask(__name__)

# We setup the metrics
if os.getenv('MIGRATE_MODE', False) not in [True, 'true', 'True', '1']:
    if not config.TEST_MODE:
        from prometheus_flask_exporter.multiprocess import GunicornInternalPrometheusMetrics
        from shared.monitoring.monitor_auth import monitor_auth
        default_labels = {'serv': 'web', 'ver': config.VERSION}
        metrics = GunicornInternalPrometheusMetrics(app, group_by='endpoint', path='/pmetrics', default_labels=default_labels, metrics_decorator=monitor_auth.login_required)
        metrics.info('app_info', 'Web App', **default_labels)

app.jinja_env.cache = {}
app.jinja_env.policies['json.dumps_kwargs'] = {'sort_keys': False}
app.jinja_env.auto_reload = config.reload_templates
app.jinja_env.undefined = jinja2.StrictUndefined if config.is_dev_mode() else jinja2.runtime.Undefined

app.jinja_env.add_extension('jinja2.ext.do')
app.jinja_env.add_extension(MarkdownExtension)
app.config['TEMPLATES_AUTO_RELOAD'] = config.reload_templates

# Add enterprise templates folder to template search path
if config.ENABLE_ENTERPRISE_FEATURES:
    import os
    # Calculate path: from oss/web_app/__init__.py, go up to root, then into enterprise
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    enterprise_templates_path = os.path.join(root_dir, 'crm', 'enterprise_features', 'views', 'templates')
    if os.path.exists(enterprise_templates_path):
        from jinja2 import ChoiceLoader, FileSystemLoader
        # Get the current loader
        current_loader = app.jinja_env.loader
        # Create a ChoiceLoader that searches both the default location and enterprise templates
        if isinstance(current_loader, ChoiceLoader):
            # If already a ChoiceLoader, add to it
            current_loader.loaders.append(FileSystemLoader(enterprise_templates_path))
        else:
            # Create a new ChoiceLoader with both loaders
            app.jinja_env.loader = ChoiceLoader([
                current_loader,
                FileSystemLoader(enterprise_templates_path)
            ])

app.config['SESSION_COOKIE_SAMESITE'] = 'None' # To allow the use of paygops within an iframe
app.config['SESSION_COOKIE_SECURE'] = True


if config.is_production_server():
    app.config['PREFERRED_URL_SCHEME'] = 'https'
    app.wsgi_app = ReverseProxied(app.wsgi_app)

if config.CACHING_ENABLED:
    cache_type = "redis"
else:
    cache_type = "null"

cache = Cache(app, config={'CACHE_TYPE': cache_type, 'CACHE_REDIS_HOST': config.REDIS_HOST, 'CACHE_REDIS_PORT': config.REDIS_PORT})

app.secret_key = config.secret_key

logger = logging.getLogger('werkzeug')

info_handler = Logger.create_handler('info.log', level=logging.DEBUG)
error_handler = Logger.create_handler('error.log', level=logging.ERROR)

logger.addHandler(info_handler)
logger.addHandler(error_handler)

app.logger.addHandler(info_handler)
app.logger.addHandler(error_handler)

login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = "login.login"
login_manager.login_message = "You need to be logged in to access this page"

# We prepare the assets
assets = Environment(app)
assets.auto_build = config.reload_templates
register_assets(assets, app.config)

from web_app.context import *
from web_app.index import *
from web_app.error_handler import *

BlueprintRegisterer.register(app)
DatabaseMapper.generate_map()
