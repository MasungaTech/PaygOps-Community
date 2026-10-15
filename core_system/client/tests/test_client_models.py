from shared.helpers.client_creator import ClientCreator
import pytest
from datetime import datetime

from pony.orm import db_session

from core_system.client.models import Client


class TestClientModel:

    @pytest.fixture(autouse=True)
    @db_session
    def _autouse_setup(self, api_client, good_api_key):
        ClientCreator.create(api_client, good_api_key, lead_data={'Name': 'Superman Test 2'})

    @db_session
    def test_get_all_clients(cls):
        res = Client.all()
        assert res.count() == Client.select().count()
        assert isinstance(res.first(), Client)

    @db_session
    def test_client_cash_account(cls):
        client = Client.all().first()
        res = client.get_cash_account()
        assert client.person.name and client.person.surname in res.FullName

        sec_res = client.get_cash_account()
        assert res.__dict__ == sec_res.__dict__


