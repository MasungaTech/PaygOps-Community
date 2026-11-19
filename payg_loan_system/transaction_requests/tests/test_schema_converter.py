from payg_loan_system.transaction_requests.services.transaction_service import BOOLEAN_SCHEMA
from worker_app.tasks.analyse_api_caller import schema_converter


class TestSchemaConverterBoolean:

    def test_false_string_via_boolean_schema(self):
        assert schema_converter("False", BOOLEAN_SCHEMA) is False

    def test_true_string_via_boolean_schema(self):
        assert schema_converter("True", BOOLEAN_SCHEMA) is True

    def test_zero_string_via_boolean_schema(self):
        assert schema_converter("0", BOOLEAN_SCHEMA) is False

    def test_one_string_via_boolean_schema(self):
        assert schema_converter("1", BOOLEAN_SCHEMA) is True

    def test_false_bool_via_boolean_schema(self):
        assert schema_converter(False, BOOLEAN_SCHEMA) is False

    def test_true_bool_via_boolean_schema(self):
        assert schema_converter(True, BOOLEAN_SCHEMA) is True

    def test_lowercase_false_via_boolean_schema(self):
        assert schema_converter("false", BOOLEAN_SCHEMA) is False


class TestSchemaConverterArray:

    STRING_ARRAY_SCHEMA = {"type": "array", "items": {"type": "string"}}

    def test_items_are_trimmed(self):
        assert schema_converter("Unavailable, Deceased", self.STRING_ARRAY_SCHEMA) == ['Unavailable', 'Deceased']

    def test_empty_string_is_empty_list(self):
        assert schema_converter("", self.STRING_ARRAY_SCHEMA) == []
