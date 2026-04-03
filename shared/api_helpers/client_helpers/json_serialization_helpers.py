import json

from .json_datetime_helpers import json_serializer, json_date_hook
from .json_validation_helpers import validate_json_schema


def serialize_data_to_json(data):
    try:
        data_json = json.dumps(data, default=json_serializer)
    except Exception as e:
        print('Data serialization error: ' + str(e))
        raise e
    return data_json


def deserialize_json_data(data):
    try:
        if data:
            result = json.loads(data, object_hook=json_date_hook)
        else:
            return {}
    except Exception as e:
        print('Data deserialization error: ' + str(e))
        raise e
    return result


def deserialize_received_json(request_result, expected_schema=None):
    result = deserialize_json_data(request_result.text)

    if expected_schema is not None:
        validate_json_schema(result, expected_schema)

    return result
