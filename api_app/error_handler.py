from flask import jsonify
from api_app import api_app
from shared.logger.loggers import LogAPI

logger = LogAPI()


@api_app.errorhandler(400)
def handle_bad_request(error):
    logger.Fatal(error)
    return jsonify({'error': "400", 'error_message': 'Bad request. Detail: '+str(error)}), 400


@api_app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '404', 'error_message': str(error), 'error_data': {}}), 404


@api_app.errorhandler(500)
def internal_error(error):
    logger.Fatal(error)
    return jsonify({'error': '500', 'error_message': str(error), 'error_data': {}}), 500
