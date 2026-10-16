from api_app import api_app
import json
from config import API_PREFIX, BASE_PLATFORM_NAME
from flask import jsonify


@api_app.route(API_PREFIX)
def api_info():
    return json.dumps({'api_name': BASE_PLATFORM_NAME, 'api_version': 'v1.0'})


@api_app.route(API_PREFIX+'/health')
def api_health():
    return jsonify({'healthy': True})
