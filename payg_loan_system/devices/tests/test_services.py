import pytest
import random
from datetime import datetime
from mock import MagicMock, mock
from payg_loan_system.devices.services.device_sort_service import DeviceSorter
from payg_loan_system.devices.factories import DeviceFactory
from tests.factories.factories import PersonFactory, ClientFactory


class TestDeviceSorter:
    @pytest.fixture
    def devices(self):
        devices = []

        for i in range(1, 4):
            entrepreneur = ClientFactory.stub(
                person=PersonFactory.stub()
            )

            entrepreneur.person.full_name = 'N{n} S{n}'.format(n=i)

            device = DeviceFactory.stub(
                SerialNumber=i,
                type=str(i),
                Mode=i,
                client=entrepreneur,
                ActiveUntil=datetime(2016, i, 1))

            device.get_offer_code = MagicMock(return_value=i)
            devices.append(device)

        random.shuffle(devices)

        return devices

    def test_by_mode_returns_mode(self):
        device = DeviceFactory.stub(Mode=2)

        assert device.Mode == DeviceSorter.by_mode(device)

    def test_by_mode_returns_type(self):
        device = DeviceFactory.stub(type="SOL")

        assert device.type == DeviceSorter.by_type(device)

    def test_by_mode_returns_serial_number(self):
        device = DeviceFactory.stub(SerialNumber='2')

        assert device.SerialNumber == DeviceSorter.by_serial_number(device)

    def test_by_active_until_returns_active_until_date(self):
        device = DeviceFactory.stub()

        assert device.ActiveUntil == DeviceSorter.by_active_until(device)

    def test_by_active_until_returns_old_date(self):
        device = DeviceFactory.stub(ActiveUntil=None)
        expected_date = datetime(2100, 1, 1, 1, 1, 1, 0)

        assert expected_date == DeviceSorter.by_active_until(device)

    def test_by_owner_returns_empty(self):
        device = DeviceFactory.stub(contract=None)

        assert ' - ' == DeviceSorter.by_owner(device)

    def test_by_owner_returns_full_name(self):
        entrepreneur = ClientFactory.stub(
            person=PersonFactory.stub()
        )

        entrepreneur.person.full_name = 'Name Test'

        device = DeviceFactory.stub()
        device.contract.client = entrepreneur

        assert 'Name Test' == DeviceSorter.by_owner(device)

    def test_by_offer_returns_empty(self):
        device = DeviceFactory.stub()
        device.get_offer_code = MagicMock(return_value=None)

        assert ' - ' == DeviceSorter.by_offer(device)

    def test_by_offer_returns_offer_code(self):
        device = DeviceFactory.stub()
        device.get_offer_code = MagicMock(return_value=1)

        assert '1' == DeviceSorter.by_offer(device)

    def test_sort_by_serial_number(self, devices):
        with mock.patch.object(DeviceSorter, 'real_field_sort', return_value=False):
            rs = DeviceSorter.sort(devices, 'serial_number:asc').resultset

        assert 1 == rs[0].SerialNumber
        assert 2 == rs[1].SerialNumber
        assert 3 == rs[2].SerialNumber

        with mock.patch.object(DeviceSorter, 'real_field_sort', return_value=False):
            rs = DeviceSorter.sort(devices, 'serial_number:desc').resultset
        assert 3 == rs[0].SerialNumber
        assert 2 == rs[1].SerialNumber
        assert 1 == rs[2].SerialNumber

    def test_sort_by_active_until(self, devices):
        with mock.patch.object(DeviceSorter, 'real_field_sort', return_value=False):
            rs = DeviceSorter.sort(devices, 'active_until:asc').resultset

        assert datetime(2016, 1, 1, 0, 0) == rs[0].ActiveUntil
        assert datetime(2016, 2, 1, 0, 0) == rs[1].ActiveUntil
        assert datetime(2016, 3, 1, 0, 0) == rs[2].ActiveUntil

        with mock.patch.object(DeviceSorter, 'real_field_sort', return_value=False):
            rs = DeviceSorter.sort(devices, 'active_until:desc').resultset
        assert datetime(2016, 3, 1, 0, 0) == rs[0].ActiveUntil
        assert datetime(2016, 2, 1, 0, 0) == rs[1].ActiveUntil
        assert datetime(2016, 1, 1, 0, 0) == rs[2].ActiveUntil

    def test_sort_by_type(self, devices):
        with mock.patch.object(DeviceSorter, 'real_field_sort', return_value=False):
            rs = DeviceSorter.sort(devices, 'type:asc').resultset

        assert str(1) == rs[0].type
        assert str(2) == rs[1].type
        assert str(3) == rs[2].type

        with mock.patch.object(DeviceSorter, 'real_field_sort', return_value=False):
            rs = DeviceSorter.sort(devices, 'type:desc').resultset
        assert str(3) == rs[0].type
        assert str(2) == rs[1].type
        assert str(1) == rs[2].type

    def test_sort_by_mode(self, devices):
        with mock.patch.object(DeviceSorter, 'real_field_sort', return_value=False):
            rs = DeviceSorter.sort(devices, 'mode:asc').resultset

        assert 1 == rs[0].Mode
        assert 2 == rs[1].Mode
        assert 3 == rs[2].Mode

        with mock.patch.object(DeviceSorter, 'real_field_sort', return_value=False):
            rs = DeviceSorter.sort(devices, 'mode:desc').resultset
        assert 3 == rs[0].Mode
        assert 2 == rs[1].Mode
        assert 1 == rs[2].Mode

    def test_sort_by_offer(self, devices):
        rs = DeviceSorter.sort(devices, 'offer:asc').resultset

        assert 1 == rs[0].get_offer_code()
        assert 2 == rs[1].get_offer_code()
        assert 3 == rs[2].get_offer_code()

        rs = DeviceSorter.sort(devices, 'offer:desc').resultset
        assert 3 == rs[0].get_offer_code()
        assert 2 == rs[1].get_offer_code()
        assert 1 == rs[2].get_offer_code()

    def test_sort_by_owner(self, devices):
        rs = DeviceSorter.sort(devices, 'offer:asc').resultset

        assert 'N1 S1' == rs[0].client.person.full_name
        assert 'N2 S2' == rs[1].client.person.full_name
        assert 'N3 S3' == rs[2].client.person.full_name

        rs = DeviceSorter.sort(devices, 'offer:desc').resultset
        assert 'N3 S3' == rs[0].client.person.full_name
        assert 'N2 S2' == rs[1].client.person.full_name
        assert 'N1 S1' == rs[2].client.person.full_name
