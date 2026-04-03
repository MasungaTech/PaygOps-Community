from tests.base_test import BaseViewTest
from pony.orm import db_session
import pytest
from payg_loan_system.devices.model.device import Device


@db_session
def get_device():
    return Device.select().first()


class TestViewDevice(BaseViewTest):
    url = 'device.view_device'
    template = 'view_device.html'

    @classmethod
    @db_session
    @pytest.fixture(autouse=True)
    def setup_method(cls, templates, context):
        cls.context = context
        cls.templates = templates
        cls.device = get_device()
        cls.params = dict(device_id=cls.device.id)
