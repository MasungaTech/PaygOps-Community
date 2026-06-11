

from core_system.operational_entities.models import ClientGroup, Cluster, Hub, Region, Village, Zone
from constants import MAX_ENTITY_LEVEL
from shared.services.settings_service import SettingsService


class OperationalEntitiesHelper:

    ENTITY_LEVELS_MAPPING = {
        -1: 'client_groups',
        0: 'villages',
        1: 'clusters',
        2: 'hubs',
        3: 'zones',
        4: 'regions'
    }

    ENTITY_NAMES_MAPPING = {v: k for k, v in ENTITY_LEVELS_MAPPING.items()}

    ENTITY_ICONS = {
        -1: 'groups',
        0: 'home',
        1: 'filter_tilt_shift',
        2: 'store',
        3: 'device_hub',
        4: 'terrain'
    }

    CLASSES = {
        -1: ClientGroup,
        0: Village,
        1: Cluster,
        2: Hub,
        3: Zone,
        4: Region
    }

    @classmethod
    def level_name_valid(cls, level_name):
        return level_name in cls.ENTITY_LEVELS_MAPPING.values()

    @classmethod
    def level_valid(cls, level):
        return level in cls.ENTITY_LEVELS_MAPPING.keys()
    
    @classmethod
    def get_level_name(cls, level):
        return cls.ENTITY_LEVELS_MAPPING[level]
    
    @classmethod
    def get_custom_level_name(cls, level):
        OperationalEntitiesConfig = SettingsService.get_setting('OperationalEntities')
        return OperationalEntitiesConfig[level]['name']
    
    @classmethod
    def get_level(cls, level_name):
        return cls.ENTITY_NAMES_MAPPING[level_name]
    
    @classmethod
    def get_icon(cls, level):
        return cls.ENTITY_ICONS.get(level, '')

    @classmethod
    def get_level_class(cls, level):
        return cls.CLASSES[level]
    
    @classmethod
    def get_level_name_class(cls, level_name):
        return cls.CLASSES[cls.get_level(level_name)]

    @classmethod
    def get_max_level_enabled(cls):
        config = SettingsService.get_setting('OperationalEntities')
        for i in range(MAX_ENTITY_LEVEL, 0, -1):
            if config[i]['enabled']:
                return i
        return 0
    
    @classmethod
    def get_permission_name(cls, level):
        return ''.join([w.capitalize() for w in cls.ENTITY_LEVELS_MAPPING[level].split('_')])