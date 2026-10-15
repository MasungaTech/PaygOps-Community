from shared.services.base_getter_service import BaseGetterService
from sales_system.lead_generator.model import LeadGenerator
from pony import orm
from shared.helpers.db_helpers import searchable_text
from shared.services.settings_service import SettingsService


class LeadGeneratorGetterService(BaseGetterService):

    OBJ_NAME = 'Lead Generator'

    @classmethod
    def get_filtered_objects(cls, current_user, search=None, active_filter=None, lead_generator_type=None, for_sync=False, **kwargs):
        generators = LeadGenerator.select()
        if not SettingsService.get_setting('FeatureToggles').get('SalesFeatures'):
            generators = generators.filter(lambda lg: lg.type == 'Default Lead Generator')
        if not current_user.can_access('ViewLeadGenerators') or (for_sync and not current_user.can_access('SyncLeadGeneratorsMobile')):
            if not current_user.can_access('ViewOwnLeadGenerators') or (for_sync and not current_user.can_access('SyncOwnLeadGeneratorMobile')):
                return LeadGenerator.select(lambda l: l.id == -1)
            generators = generators.filter(lambda lg: lg.person == current_user.person)
        if search:
            from core_system.phone_numbers.services.phone_number_getter import PhoneNumberGetterService
            persons = PhoneNumberGetterService.find_persons_if_search_is_number(search)
            search = searchable_text(search)
            generators = generators.filter(lambda e: search in e.person.searchable_name or e.person in persons)
        if active_filter in ['default', 'active']:
            generators = generators.filter(lambda lg: lg.working == True)
        if lead_generator_type:
            generators = generators.filter(lambda lg: lg.type == lead_generator_type)
        elif active_filter == 'inactive':
            generators = generators.filter(lambda lg: lg.working != True)
        return generators

    @classmethod
    def get_list_for_mobile(cls, current_user, cached_ids):
        return cls.get_list(current_user, for_sync=True)
