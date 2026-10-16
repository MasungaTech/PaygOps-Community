from pony.orm import flush, rollback, IntegrityError, CacheIndexError, TransactionIntegrityError
from sales_system.leads.models.lead_status import LeadStatus
from sales_system.leads.models.status_category import StatusCategory
from shared.logger.loggers import Error
from shared.services.base_getter_service import BaseGetterService
from shared.services.settings_service import SettingsService


class LeadStatusService(BaseGetterService):

    STATUS_CATEGORY_ORDER = [
        StatusCategory.to_be_convinced,
        StatusCategory.awaiting_information,
        StatusCategory.awaiting_decision,
        StatusCategory.awaiting_payment,
        StatusCategory.awaiting_delivery,
        StatusCategory.installed,
        StatusCategory.inactive,
        StatusCategory.discarded,
        StatusCategory.cancelled
    ]

    @classmethod
    def get_filtered_objects(cls, current_user, categories=None, ids=None, **kwargs):
        statuses = LeadStatus.select()
        if categories:
            statuses = statuses.filter(lambda s: s.category in categories)
        
        if ids:
            statuses = statuses.filter(lambda s: s.id in ids)
        return statuses

    @classmethod
    def edit_statuses(cls, data):
        for cat in data:
            if not StatusCategory.valid_code(cat):
                raise Error(f'The {cat} category is not a valid status category')
            if not data[cat]:
                raise Error(f'You cannot delete all the statuses in {getattr(StatusCategory, cat)}.')
            ids = []
            for order, sdata in enumerate(data[cat]):
                status_id = sdata.get('id')
                if not status_id:
                    status = LeadStatus.get(name=sdata.get('name'), category=getattr(StatusCategory, cat))
                    if not status:
                        try:
                            status = LeadStatus(name=sdata['name'], color=sdata['color'], order=order,
                                            category=getattr(StatusCategory, cat))
                            flush()
                        except (IntegrityError, CacheIndexError, TransactionIntegrityError):
                            rollback()
                            raise Error(f'Status names must be unique. "{sdata["name"]}" is duplicated.')
                else:
                    status = LeadStatus.get(name=sdata.get('name'), category=getattr(StatusCategory, cat))
                    if not status:
                        status = LeadStatus.get(id=status_id)
                    if not status:
                        status = LeadStatus(id=status_id, name=sdata['name'], color=sdata['color'], order=order,
                                            category=getattr(StatusCategory, cat))
                    status.name = sdata['name']
                    status.color = sdata['color'] or 'gray'
                    status.order = order
                ids.append(int(status.id))
            for status in LeadStatus.select(lambda s: s.category == getattr(StatusCategory, cat) and s.id not in ids):
                if status.leads.count():
                    raise Error(f'Status #{status.id} ({status.name}) cannot be deleted because it has leads attached.')
                status.delete()
    
    @classmethod
    def edit_lead_restricted_statuses(cls, data):
        status_categories = StatusCategory.to_dict()
        status = data.get('status')
        if status and status in status_categories.keys():
            keys = list(status_categories.keys())
            index_of_key = keys.index(status)
            return {key: value for key, value in status_categories.items() if keys.index(key) >= index_of_key}
        return {}

    @classmethod
    def get_restricted_statuses(cls):
        restrict_from_status_id = SettingsService.get_setting('PersonalDetailsEditingRestrictions')
        if not restrict_from_status_id:
            return []
        restrict_from_status = LeadStatus.get(id=restrict_from_status_id)
        if not restrict_from_status:
            return []
        first_restricted_cat = restrict_from_status.category
        status_categories = cls.STATUS_CATEGORY_ORDER
        # We get all of the restricted categories
        restricted_categories = status_categories[status_categories.index(first_restricted_cat)+1:]
        return LeadStatus.select(lambda s: s.category in restricted_categories or (
            s.category == first_restricted_cat and s.order >= restrict_from_status.order
        ))

    @classmethod
    def lead_is_in_restricted_status(cls, lead):
        return lead.status in cls.get_restricted_statuses()

    @classmethod
    def get_allowed_statuses_for_new_lead(cls, user=None):
        statuses = LeadStatus.select(lambda s: s.category == StatusCategory.to_be_convinced or
                                 s.category == StatusCategory.awaiting_information)
        if user and not user.can_access_in_any('MoveToRestrictedStatusLeads'):
            restricted_statuses = SettingsService.get_setting('statusTransitionRestrictions').get('1001', [])
            statuses = statuses.filter(lambda s: s.id not in restricted_statuses)
        return statuses

    @classmethod
    def get_status(cls, key):
        if key is None:
            return None
        try:
            status = LeadStatus.get(id=key)
            if not status:
                raise Error('INVALID_LEAD_STATUS_ID')
        except ValueError:
            status = LeadStatus.select(lambda s: s.name.lower() == key.lower()).first()
            if not status:
                raise Error('The lead status provided was not found', code='INVALID_LEAD_STATUS')
        return status
