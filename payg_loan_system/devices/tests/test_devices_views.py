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

    @pytest.fixture(autouse=True)
    def _autouse_setup(self, templates, context):
        self.context = context
        self.templates = templates
        self.device = get_device()
        self.params = dict(device_id=self.device.id)
