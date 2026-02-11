from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService
from payg_loan_system.devices.model.device import Device
from shared.services.settings_service import SettingsService
from payg_loan_system.offers.models import Offer
from sales_system.lead_generator.model import LeadGenerator
from sales_system.leads.models.lead_status import LeadStatus
from core_system.operational_entities.models import ClientGroup, Village


class LeadMobileAdapter:

    def __init__(self, data_to_adapt, user):
        self.user = user
        self.data_to_adapt = data_to_adapt

    def adapt_to_crm_from_client(self):
        offer = self.data_to_adapt.get('fk_offer', None)
        if offer is None:
            offer = self.data_to_adapt.get('offer', None)
        return {
            'id': self.data_to_adapt.get('crmId'),
            'client_mobile': self.data_to_adapt.get('fk_client'),
            'status': self.get_id_from_mobile_uuid(LeadStatus, self.data_to_adapt['fk_status']),
            'generator': self.get_id_from_mobile_uuid(LeadGenerator, self.data_to_adapt['fk_generator']),
            'offer': self.get_id_from_mobile_uuid(Offer, offer),
            'mobile_uuid': self.data_to_adapt.get('mobileUuid', None)
        }

    def adapt_to_crm(self):
        phone_number = self.data_to_adapt.get('phoneNumber')
        phone_numbers_raw = self.data_to_adapt.get('phoneNumbers')
        if not phone_number and len(phone_numbers_raw) > 0:
            phone_number = phone_numbers_raw[0]
        if phone_numbers_raw:
            phone_numbers = phone_numbers_raw
        else:
            phone_numbers = [phone_number]

        offer = self.data_to_adapt.get('fk_offer', None)
        if offer is None:
            offer = self.data_to_adapt.get('offer', None)
        device = None
        device_uuid = self.data_to_adapt.get('allocatedDevice', None)
        if device_uuid:
            device = DeviceGetterService.get_from_user_and_properties(self.user, mobile_uuid=device_uuid, strict=True)
        return {
            'id': self.data_to_adapt.get('crmId'),
            'status': self.get_id_from_mobile_uuid(LeadStatus, self.data_to_adapt['fk_status']),
            'name': self.data_to_adapt['name'],
            'surname': self.data_to_adapt['surname'],
            'generator': self.get_id_from_mobile_uuid(LeadGenerator, self.data_to_adapt['fk_generator']),
            'l0_entity_id': self.get_id_from_mobile_uuid(Village, self.data_to_adapt['village']),
            'preferred_phone_number': phone_number,
            'gender': self._adapt_gender(self.data_to_adapt.get('gender')),
            'entry_date': self.data_to_adapt['entryDate'],
            'generation_date': self.data_to_adapt['generationDate'],
            'modified_date': self.data_to_adapt.get('modifiedDate'),
            'home': self.data_to_adapt['homeUse'],
            'business': self.data_to_adapt['businessUse'],
            'offer': self.get_id_from_mobile_uuid(Offer, offer),
            'birthdate': self.data_to_adapt['birthDate'],
            'status_comment': self.data_to_adapt.get('statusChangeComment', ''),
            'next_contact': self.data_to_adapt.get('nextContactDate', ''),
            'picture_id': self.data_to_adapt.get('picture', None),
            'phone_numbers': phone_numbers,
            'sms_language': self.data_to_adapt.get('smsLanguage', None),
            'verbal_language': self.data_to_adapt.get('verbalLanguage', ''),
            'mobile_uuid': self.data_to_adapt.get('mobileUuid', None),
            'gps_latitude': self.data_to_adapt.get('gpsLat', None),
            'gps_longitude': self.data_to_adapt.get('gpsLon', None),
            'planned_delivery_date': self.data_to_adapt.get('plannedDeliveryDate', None),
            'offer_editing_locked': self.data_to_adapt.get('offerEditingLocked', True),
            'client_group_id': self.get_id_from_mobile_uuid(ClientGroup, self.data_to_adapt.get('fk_clientGroup', None)),
            'custom_id': self.data_to_adapt.get('customIdentifier', None),
            'allocated_device': device.composed_serial if device else None,
            'portfolio_id': self.data_to_adapt.get('fk_portfolio', None)
        }

    def _adapt_gender(self, gender_from_mobile):
        if gender_from_mobile == 'male':
            return 'Male'
        elif gender_from_mobile == 'female':
            return 'Female'
        else:
            return gender_from_mobile

    def get_id_from_mobile_uuid(self, entity, mobile_uuid):
        if not mobile_uuid:
            return None
        result = entity.get(mobile_uuid=mobile_uuid)
        return result.id if result else None
