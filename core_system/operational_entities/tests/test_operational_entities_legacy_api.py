from core_system.operational_entities.models import Hub
from core_system.operational_entities.services.edit_operational_entity_service import EditOperationalEntityService
from core_system.operational_entities.services.legacy_operational_entities_services import EditClusterService
from core_system.users.models.user_model import User
from api_app.tests.base_api_test import BaseAPITest
from pony import orm


class TestClusterAPI(BaseAPITest):
    BASE_URL = '/clusters'
    SAMPLE_DATA = {
        "name": "Super Cluster 1",
        "hub_id": 1,
        "manager_user_id": 1
    }
    EDIT_DATA = {
        "name": "Super Cluster 2",
        "hub_id": 1
    }
    ADD_NEW_ID = True

    @orm.db_session
    def setup_class(self):

        SHOP_DATA = {
            'name': 'Super Shop 0',
            'level': 2,
            'user_in_charge_id': User.select().first().id
        }
        user = User.get(username="super_admin@test.com")
        this_shop = EditOperationalEntityService.add_from_data_and_user(SHOP_DATA, user)
        orm.flush()
        self.SAMPLE_DATA['hub_id'] = int(this_shop.code)
        self.SAMPLE_DATA['manager_user_id'] = User.select().first().id

        self.EDIT_DATA['hub_id'] = int(this_shop.code)
        self.EDIT_DATA['manager_user_id'] = User.select().first().id


class TestVillageAPI(BaseAPITest):
    BASE_URL = '/villages'
    SAMPLE_DATA = {
        "name": "Super Village 1",
        "cluster_id": 1,
        "gps_longitude": None,
        "gps_latitude": None
    }
    EDIT_DATA = {
        "name": "Super Village 2",
        "gps_longitude": 1.1,
        "gps_latitude": 2.2
    }
    ADD_NEW_ID = True

    @orm.db_session
    def setup_class(self):
        this_shop = Hub.select().first()
        orm.flush()
        CLUSTER_DATA = {
            "name": "TestVillage TestCluster0",
            "hub_id": this_shop.id
        }
        this_cluster = EditClusterService.add_from_data_and_user(CLUSTER_DATA, User.get(username="super_admin@test.com"))
        orm.flush()
        self.SAMPLE_DATA['cluster_id'] = this_cluster.id
