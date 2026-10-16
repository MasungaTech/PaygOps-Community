from jsonschema import validate, ValidationError


def validate_json_schema(json_payload, expected_schema=None):
    if expected_schema is not None:
        try:
            validate(json_payload, expected_schema)
        except ValidationError as e:
            print('JSON Payload does not match expected schema:' + str(e))
            raise e
