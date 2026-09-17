from core_system.users.models.user_model import User
from shared.services.base_getter_service import BaseGetterService
from payg_loan_system.offers.models import Offer, OfferType
from tests.support.user_stub import UserStub
from shared.services.settings_service import SettingsService
from shared.services.sorter import Sorter
from pony import orm


class ListOfferService(BaseGetterService):

    OBJ_NAME = 'Contract Offer'

    @classmethod
    def get_filtered_objects(cls, current_user, active_filter='all', search='', otype=None, for_lead_entity=None,
        for_client_entity=None, in_use_for_new_clients_only=None, current_offer=None, in_use=None, **kwargs):

        if isinstance(current_user, UserStub):
            current_user = User[current_user.id]
        offers = Offer.select().order_by(lambda offer: offer.code)

        lum_sum_enabled = SettingsService.get_setting('FeatureToggles').get('LumpSumContracts')
        loan_enabled = SettingsService.get_setting('FeatureToggles').get('LoanAndSubscriptionContracts')
        if not lum_sum_enabled and not loan_enabled:
            return offers.filter(lambda offer: offer.code == 'TDO')
        if active_filter == ['all']:
            pass
        elif active_filter in ['default', 'active']:
            offers = offers.filter(lambda offer: offer.in_use_for_new_clients == True)
        elif active_filter == 'inactive':
            offers = offers.filter(lambda offer: offer.in_use_for_new_clients != True)
        
        if OfferType.valid(otype):
            offers = offers.filter(lambda o: o.type == otype)
        
        if in_use_for_new_clients_only:
            offers = offers.filter(lambda offer: offer.in_use_for_new_clients is True or offer is current_offer)
        
        if in_use:
            offers = offers.filter(lambda o: o.in_use)
            if current_offer:
                offers = offers.filter(lambda o: o.type == current_offer.type and o != current_offer)
                if (
                    SettingsService.get_setting('ContractDeviceRestrictions') != 'no_device'
                    and not current_offer.linked_to_product
                ):
                    offers = offers.filter(lambda o: o.linked_to_product == False)

        if search:
            offers = offers.filter(lambda o: search.lower() in (
                    o.name + ' ' + o.code + ' ' + str(o.id)
            ).lower())
        if for_lead_entity:
            # Align with AddonOfferVersionGetterService.restrict_versions_to_entities (.ascendants)
            ascendant_ids = [e.id for e in for_lead_entity.ascendants]
            offers = offers.filter(
                lambda o: o is current_offer
                or not o.entities_allowed_for_leads
                or o.entities_allowed_for_leads.filter(lambda e: e.id in ascendant_ids).count() > 0
            )
        if for_client_entity:
            ascendant_ids = [e.id for e in for_client_entity.ascendants]
            offers = offers.filter(
                lambda o: o is current_offer
                or not o.entities_allowed_for_contracts
                or o.entities_allowed_for_contracts.filter(lambda e: e.id in ascendant_ids).count() > 0
            )
        return offers


class OfferSorter(Sorter):

    @staticmethod
    def real_field_sort(field_name, desc=False):
        options = {
            'id': lambda l: l.id,
            'name': lambda l: l.name,
            'code': lambda l: l.code
        }
        options_desc = {
            'id': lambda l: orm.desc(l.id),
            'name': lambda l: orm.desc(l.name),
            'code': lambda l: orm.desc(l.code)
        }
        obj = options_desc if desc else options
        return obj.get(field_name, lambda l: l.time)
