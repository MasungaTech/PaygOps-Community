from pony import orm
from core_system.users.services.user_getter_service import UserGetterService
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from core_system.operational_entities.models import Cluster, Hub, Village
from core_system.users.models.user_model import User
from shared.helpers.picture_helper import getGPSCoordinatesFromPicture, storePicture
from shared.services.base_getter_service import BaseGetterService
from shared.logger.loggers import Error
from tests.support.user_stub import UserStub
from shared.services.base_service import BaseService



class ClusterGetterService(BaseGetterService):

    OBJ_NAME = 'Cluster'

    @classmethod
    def get_filtered_objects(cls, current_user, **kwargs):
        return OperationalEntitiesGetterService.get_list(current_user, level=1)

    @classmethod
    def get_managed_by_user(cls, user):
        return Cluster.select(lambda c: c.user_in_charge == user)


class EditClusterService(BaseService):

    @classmethod
    def get_affected_entity(cls, data, user):
        shop = Hub.get(code=str(data.get('hub_id')))
        if not shop:
            shop = Hub.get(id=data.get('hub_id'))
        return shop

    @classmethod
    def _add_from_data_and_user(cls, data, user):
        name = data.get('name')
        if not name:
            raise Error('NAME_REQUIRED')
        shop = cls.get_affected_entity(data, user)
        if not shop:
            raise Error('HUB_REQUIRED')
        cls._check_if_name_exists(name, shop)
        manager = UserGetterService.get_from_user_and_id(user, data.get('manager_user_id'))
        this_cluster = Cluster(
            name=data.get('name'),
            parent=shop,
            user_in_charge=manager
        )
        orm.flush()
        this_cluster.code = str(this_cluster.id)
        return this_cluster

    @classmethod
    def _edit_from_data_and_user(cls, cluster, data, user):
        if data.get('hub_id'):
            shop = Hub.get(code=str(data.get('hub_id'))) or Hub.get(id=data.get('hub_id'))
        else:
            shop = cluster.parent 
        if not shop:
            raise Error('HUB_REQUIRED')
        name = data.get('name', cluster.name)
        cls._check_if_name_exists(name, shop, existing_cluster=cluster)
        cluster.name = name
        cluster.parent = shop
        manager_user_id = data.get('manager_user_id')
        if manager_user_id:
            manager = UserGetterService.get_from_user_and_id(user, manager_user_id, strict=True)
            cluster.user_in_charge = manager
        return cluster

    @classmethod
    def get_human_readable_message(cls, error, user=None):
        if str(error) == 'NAME_REQUIRED':
            return 'The name is required.'
        elif str(error) == 'HUB_REQUIRED':
            return 'A valid hub ID is required.'
        elif str(error) == 'INVALID_MANAGER_USER_ID':
            return 'The provided manager User ID is invalid.'
        elif str(error) == 'NAME_ALREADY_TAKEN':
            return 'The name is already in use by a cluster in the same hub.'
        return 'Unknown error'

    @classmethod
    def _check_if_name_exists(cls, name, shop, existing_cluster=None):
        matching_clusters = orm.select(cluster for cluster in Cluster
                                       if cluster.name == name
                                       and cluster.parent == shop
                                       and cluster != existing_cluster)
        if matching_clusters.count() != 0:
            raise Error('NAME_ALREADY_TAKEN')

class ShopGetterService(BaseGetterService):

    OBJ_NAME = 'Shop'

    @classmethod
    def get_filtered_objects(cls, current_user=None, search=None, **kwargs):
        shops = OperationalEntitiesGetterService.get_list(current_user, level=2)
        if search:
            shops = shops.filter(lambda s: search.lower() in s.name.lower())
        return shops


class EditShopService(BaseService):

    @classmethod
    def _add_from_data_and_user(cls, data, user):
        name = data.get('name')
        if not name:
            raise Error('NAME_REQUIRED')
        cls._check_if_name_exists(name)
        this_shop = Hub(name=data.get('name'))
        orm.flush()
        this_shop.code = str(this_shop.id)
        return this_shop

    @classmethod
    def _edit_from_data_and_user(cls, shop, data, user):
        name = data.get('name', shop.name)
        cls._check_if_name_exists(name, existing_shop=shop)
        shop.name = name

    @classmethod
    def get_human_readable_message(cls, error, user=None):
        if str(error) == 'NAME_REQUIRED':
            return 'The hub name is required.'
        elif str(error) == 'NAME_ALREADY_TAKEN':
            return 'The hub name is already in use by another hub.'
        return 'Unknown error'

    @classmethod
    def _check_if_name_exists(cls, name, existing_shop=None):
        matching_shops = orm.select(shop for shop in Hub
                                    if shop.name == name
                                    and shop != existing_shop)
        if matching_shops.count() != 0:
            raise Error('NAME_ALREADY_TAKEN')


class VillageGetterService(BaseGetterService):

    OBJ_NAME = 'Village'

    @classmethod
    def get_filtered_objects(cls, current_user, **kwargs):
        return OperationalEntitiesGetterService.get_list(current_user, level=0)

    @staticmethod
    def get_villages_in_shop(shop):
        return orm.select(V for V in Village if V.parent.parent == shop)

    @staticmethod
    def get_villages_in_cluster(user):
        return orm.select(V for V in Village if V.inherited_user_in_charge == user)

    @classmethod
    def get_villages_in_user_shop(cls, user):
        if isinstance(user, UserStub):
            return Village.select(lambda v: v.id == None)
        return cls.get_villages_in_shop(user.shop)

    @classmethod
    def get_villages_in_user_cluster(cls, user):
        if isinstance(user, UserStub):
            return Village.select(lambda v: v.id == None)
        return cls.get_villages_in_cluster(user)


class EditVillageService(BaseService):

    @classmethod
    def get_affected_entity(cls, data, user, **kwargs):
        cluster = Cluster.get(code=str(data.get('cluster_id')))
        if not cluster:
            cluster = Cluster.get(id=data.get('cluster_id'))
        if not cluster:
            raise Error("Cluster not found")
        return cluster

    @classmethod
    def _add_from_data_and_user(cls, data, user):
        name = data.get('name')
        if not name:
            raise Error('NAME_REQUIRED')
        cluster = cls.get_affected_entity(data, user)
        if not cluster:
            raise Error('CLUSTER_REQUIRED')
        cls._check_if_name_exists(name, cluster)
        this_village = Village(
            name=data.get('name'),
            parent=cluster,
            longitude=float(data.get('gps_longitude')) if data.get('gps_longitude') else None,
            latitude=float(data.get('gps_latitude')) if data.get('gps_latitude') else None,
            admin_contact_name=data.get('chief_name', ''),
            admin_phone_number=data.get('chief_number', ''),
            population=int(data.get('population')) if data.get('population') else None,
            description=data.get('notes', ''),
        )
        orm.flush()
        this_village.code = str(this_village.id)
        return this_village
    
    @classmethod
    def _edit_from_data_and_user(cls, village, data, user):
        if data.get('cluster_id'):
            cluster = Cluster.get(code=str(data.get('cluster_id'))) or Cluster.get(id=data.get('cluster_id'))
        else:
            cluster = village.parent
        if not cluster:
            raise Error('CLUSTER_REQUIRED')
        name = data.get('name', village.name)
        cls._check_if_name_exists(name, cluster, existing_village=village)
        village.name = name
        village.parent = cluster
        village.admin_contact_name = data.get('chief_name', village.admin_contact_name)
        village.admin_phone_number = data.get('chief_number', village.admin_phone_number)
        village.longitude = cls._convert_if_present('gps_longitude', data, 'float', village.longitude)
        village.latitude = cls._convert_if_present('gps_latitude', data, 'float', village.latitude)
        village.population = cls._convert_if_present('population', data, 'int', village.population)
        village.description = data.get('notes', village.description)
        picture_uuid = data.get('picture_id')
        if picture_uuid:
            cls._update_gps_coordinates_from_picture(village, picture_uuid)
        return village

    @classmethod
    def get_human_readable_message(cls, error, user=None):
        if str(error) == 'NAME_REQUIRED':
            return 'The name is required.'
        elif str(error) == 'CLUSTER_REQUIRED':
            return 'A valid cluster ID is required.'
        elif str(error) == 'NAME_ALREADY_TAKEN':
            return 'The name is already in use by a village in the same cluster.'
        return 'Unknown error'

    @classmethod
    def _convert_if_present(cls, value_name, data, data_type, default):
        result = data.get(value_name, default)
        if result:
            return int(result) if data_type == 'int' else float(result)
        return None

    @classmethod
    def _update_gps_coordinates_from_picture(cls, village, picture_uuid):
        this_picture = storePicture(picture_uuid)
        if this_picture is not None:
            gps_coordinates = getGPSCoordinatesFromPicture(this_picture)
            if gps_coordinates is not None:
                village.latitude = gps_coordinates[0]
                village.longitude = gps_coordinates[1]

    @classmethod
    def _check_if_name_exists(cls, name, cluster, existing_village=None):
        matching_villages = orm.select(village for village in Village
                                       if village.name == name
                                       and village.parent == cluster
                                       and village != existing_village)
        if matching_villages.count() != 0:
            raise Error('NAME_ALREADY_TAKEN')
