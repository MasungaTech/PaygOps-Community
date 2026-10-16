from shared.api_helpers.server_helpers.jwt_and_schema_verification import verify
from flask_restful import Resource, request
import dateutil.parser

test_schema = {
    "properties": {
        "test_name": {
          "type": "string"
        },
        "test_datetime": {
          "type": "string"
        },
        "test_number": {
          "type": "integer"
        }
    },
    "required": ["test_name", "test_number"]
}


class TestResource(Resource):

    @verify(permissions=['AddDevices'])
    def get(self):
        return {'Authentified': True}


    @verify(permissions=['AddDevices'], schema=test_schema)
    def post(self):
        # if test_name == date_test, then we get the date and transform it
        if request.json['test_name'] == 'test_datetime':
            received_time = dateutil.parser.parse(request.json['test_datetime'])
            return {'converted_datetime': received_time.strftime('%m/%d/%Y')}
        else:
            return {'test_result': 'all good?'}
