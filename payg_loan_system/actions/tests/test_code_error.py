import pytest

from payg_loan_system.actions.helpers.code_error import handle_device_code_error


class TestSolarisCodeError:
    @pytest.mark.parametrize("test_input, response", [
        ('CLIENT_HAS_NO_DEVICE', {'success': False,
                                  'status': 'CLIENT_HAS_NO_DEVICE'}),
        ('DEVICE_NOT_PREREGISTERED', {'success': False,
                                      'status': 'DEVICE_NOT_PREREGISTERED'}),
        ('', {'success': False,
              'status': 'UNKNOWN_ERROR',
              'error_message': ''})
    ])
    def test_solaris_code_error_handler(self, test_input, response):
        resp = handle_device_code_error(test_input)
        assert resp == response
