from core_system.person.models.person_model import Person
from core_system.person.services.person_getter_service import PersonGetterService
from payg_loan_system.contracts.services.addons.addon_offer_getter_service import AddonOfferGetterService
from shared.helpers.date_helper import parse_datetime
from shared.services.base_getter_service import BaseGetterService
from payg_loan_system.contracts.models.contract_status import ContractStatus
from pony.orm.core import select
from payg_loan_system.contracts.models.addons_model import AddOnLoanExtensionMode, AddOnOffer, AddOnType, ContractAddOn, AddOnOfferVersion


class AddonListService(BaseGetterService):

    OBJ_NAME = 'Add-on'

    @classmethod
    def get_from_filtered_view(cls, user, view=None, offer_id=None, **kwargs):

        extra = {}
        if view == 'managed_by_me':
            extra = dict(managed_by=user)
        elif view == 'generated_by_me':
            extra = dict(generated_by=user)
        
        if offer_id:
            offer = AddonOfferGetterService.get_from_user_and_id(user, offer_id)
            if offer:
                extra.update({'offer': offer})

        addons = cls.get_list(user, **kwargs, **extra)
        return addons

    @classmethod
    def get_filtered_objects(
        cls, current_user, search=None, entity=None, portfolio=None, client_group=None,
        status=None, managed_by=None, generated_by=None, contract_reference='', lead_id=None, addon_reference=None,
        offer_type=None, offer=None, offer_id=None, offer_version_id=None,
        offer_code=None, offer_name=None, loan_mode=None, addon_type=None,
        from_date=None, to_date=None, offer_version=None,
        approved=None, delivered=None, cancelled=None, paid=None,
        planned_delivery_date_to=None, planned_delivery_date_from=None,
        **kwargs
    ):
        
        if current_user.can_access_in_all('ViewAddOns') and not entity and not portfolio and not client_group and not managed_by and not generated_by:
            addons = ContractAddOn.select()
        else:
            persons = PersonGetterService.get_list(
                current_user, permission="ViewAddOns", entity=entity, portfolio=portfolio,
                client_group=client_group, managed_by=managed_by, generated_by=generated_by
            )
            addons = select(a for a in ContractAddOn if a.cached_person in persons)
        addons = addons.prefetch(ContractAddOn.offer_version, AddOnOfferVersion.offer)

        if addon_reference:
            addons = addons.filter(lambda a: addon_reference.lower() in a.reference.lower())

        if contract_reference:
            # This is not recommended, the parameter should be contract and use the BaseGetterService.preprocess_list_filters
            # to get the proper contract from its contract_reference for the current user taking to account permissions
            addons = addons.filter(lambda a: a.contract.reference == contract_reference)
        if lead_id:
            # This is not recommended, the parameter should be lead and use the BaseGetterService.preprocess_list_filters
            # to get the proper lead from its lead_id for the current user taking to account permissions
            addons = addons.filter(lambda a: a.lead.id == lead_id)
        if search:
            addons = addons.filter(
                lambda a: search.lower() in (
                    a.contract.client.full_name + ' ' + str(a.contract.client.id) +
                    a.reference
                ).lower()
            )
        if offer_type:
            addons = addons.filter(lambda a: a.offer_version.offer.type.lower() == offer_type.lower())
        addon_type = addon_type or kwargs.get('type')
        if addon_type:
            addons = addons.filter(lambda a: a.offer_version.offer.type.lower() == addon_type.lower())
        if offer:
            addons = addons.filter(lambda a: a.offer_version.offer == offer)
        if offer_id:
            offer_ids = offer_id if isinstance(offer_id, list) else [offer_id]
            normalized_offer_ids = []
            for oid in offer_ids:
                if oid is None or oid == '':
                    continue
                try:
                    normalized_offer_ids.append(int(oid))
                except (TypeError, ValueError):
                    continue
            if normalized_offer_ids:
                addons = addons.filter(lambda a: a.offer_version.offer.id in normalized_offer_ids)
        if offer_version_id:
            version_ids = offer_version_id if isinstance(offer_version_id, list) else [offer_version_id]
            normalized_version_ids = []
            for vid in version_ids:
                if vid is None or vid == '':
                    continue
                try:
                    normalized_version_ids.append(int(vid))
                except (TypeError, ValueError):
                    continue
            if normalized_version_ids:
                addons = addons.filter(lambda a: a.offer_version.id in normalized_version_ids)
        if offer_code:
            addons = addons.filter(lambda a: a.offer_version.offer.code.lower() == offer_code.lower())
        if offer_name:
            addons = addons.filter(lambda a: offer_name.lower() in a.offer_version.offer.name.lower())
        if loan_mode:
            addons = addons.filter(lambda a: a.loan_mode and a.loan_mode.lower() == loan_mode.lower())
        if offer_version:
            addons = addons.filter(lambda a: a.offer_version == offer_version)
        if from_date:
            addons = addons.filter(lambda a: a.time_created >= from_date)
        if to_date:
            addons = addons.filter(lambda a: a.time_created <= to_date)
        if approved is not None:
            addons = addons.filter(lambda a: (not a.pending) == approved)
        if delivered is not None:
            addons = addons.filter(lambda a: a.delivered == delivered)
        if cancelled is not None:
            addons = addons.filter(lambda a: a.cancelled == cancelled)
        if paid is not None:
            addons = addons.filter(lambda a: a.paid == paid)
        if planned_delivery_date_to:
            planned_date_to = parse_datetime(planned_delivery_date_to)
            lead_addons_ids = select(a.id for a in addons.filter(lambda a: a.lead.agreedDeliveryDate <= planned_date_to))[:]
            addons = addons.filter(lambda a: a.planned_delivery_date <= planned_date_to or a.id in lead_addons_ids)
        if planned_delivery_date_from:
            planned_date_from = parse_datetime(planned_delivery_date_from)
            lead_addons_ids = select(a.id for a in addons.filter(lambda a: a.lead.agreedDeliveryDate >= planned_date_from))[:]
            addons = addons.filter(lambda a: a.planned_delivery_date >= planned_date_from or a.id in lead_addons_ids)
        return cls.status_filter(addons, status)

    @classmethod
    def status_filter(cls, addons, status):
        if status and status != 'all':
            addons = addons.filter(lambda a: getattr(a, status))
        return addons
    
    @classmethod
    def get_list_for_mobile(cls, current_user, cached_ids, **kwargs):
        # This happens only with mobile app in v3.9.0 or below, could be removed later
        if 'contract' not in cached_ids:
            relevant_clients_ids = cached_ids['client']
            contracts = current_user.get_relevant_contracts_for_mobile(relevant_clients_ids)
            cached_ids['contract'] = select(e.id for e in contracts)[:]
        contract_ids = cached_ids['contract']
        leads_ids = cached_ids['lead']
        addons = ContractAddOn.select(lambda a: a.lead.id in leads_ids or a.contract.id in contract_ids)
        return addons
