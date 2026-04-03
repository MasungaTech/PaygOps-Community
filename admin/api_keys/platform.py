from flask import jsonify
from . import api_system
from web_app import context


@api_system.route('/version', methods=['GET'])
def version():
    return jsonify(context.app_version())
