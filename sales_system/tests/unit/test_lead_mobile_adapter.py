from payg_loan_system.offers.models import Offer
from core_system.operational_entities.models import Village
from sales_system.lead_generator.model import LeadGenerator
from sales_system.leads.models.lead_status import LeadStatus
from pony import orm

from sales_system.leads.mobile_adapter import LeadMobileAdapter
from shared.services.settings_service import SettingsService


class TestLeadMobileAdapter:
    @orm.db_session
    def test_it_adapts_mobile_incoming_data_to_crm_standard(self, super_admin_user):
        mobile_incoming_data = self.adapted_to_mobile_descriptor()

        result = LeadMobileAdapter(mobile_incoming_data, super_admin_user()).adapt_to_crm()

        assert result == self.adapted_to_crm_descriptor()


    def expected_mobile_keys(self):
        return [
            'crmId',
            'statusId',
            'name',
            'surname',
            'generatorCrmId',
            'village',
            'phoneNumber',
            'homeUse',
            'businessUse',
            'gender',
            'generationDate',
            'modifiedDate',
            'birthDate',
            'offer',
            'statusChangeComment',
            'nextContactDate',
            'picture',
        ]

    def adapted_to_crm_descriptor(self):
        return {
            'id': None,
            'status': 12,
            'name': 'john',
            'surname': 'cobra',
            'generator': 1,
            'l0_entity_id': Village.select().first().id,
            'preferred_phone_number': '+2340001112224',
            'gender': 'Male',
            'entry_date': '2018-11-28T00:00:00.000Z',
            'generation_date': '2018-11-28T00:00:00.000Z',
            'gps_latitude': None,
            'gps_longitude': None,
            'modified_date': '2018-11-28T11:22:33.444Z',
            'home': False,
            'business': True,
            'birthdate': '1978-11-28T11:22:33.444Z',
            'offer': 888,
            'status_comment': 'Good lad!',
            'next_contact': '2018-11-29T11:22:33.444Z',
            'picture_id': None,
            'planned_delivery_date': None,
            'sms_language': None,
            'verbal_language': 'English',
            'phone_numbers': ['+2340001112224'],
            'mobile_uuid': 'fake-uuid',
            'offer_editing_locked': True,
            'client_group_id': None,
            'custom_id': None,
            'allocated_device': None,
            'portfolio_id': None
        }

    def adapted_to_mobile_descriptor(self):
        return {
            'crmId': None,
            'fk_status': self.get_mobile_uuid_from_id(LeadStatus, 12),
            'name': 'john',
            'surname': 'cobra',
            'fk_generator': self.get_mobile_uuid_from_id(LeadGenerator, 1),
            'village': Village.select().first().mobile_uuid,
            'phoneNumber': self._add_phone_extension('0001112224'),
            'homeUse': False,
            'businessUse': True,
            'gender': 'male',
            'generationDate': '2018-11-28T00:00:00.000Z',
            'entryDate': '2018-11-28T00:00:00.000Z',
            'modifiedDate': '2018-11-28T11:22:33.444Z',
            'birthDate': '1978-11-28T11:22:33.444Z',
            'offer': self.get_mobile_uuid_from_id(Offer, 888),
            'statusChangeComment': 'Good lad!',
            'nextContactDate': '2018-11-29T11:22:33.444Z',
            'picture': None,
            'phoneNumbers': [self._add_phone_extension('0001112224')],
            'smsLanguage': None,
            'verbalLanguage': 'English',
            'mobileUuid': 'fake-uuid',
            'offerEditingLocked': True,
            'fk_clientGroup': None
        }

    def _add_phone_extension(self, number):
        return "+"+SettingsService.get_setting('PhoneExtension')+number

    @orm.db_session
    def get_mobile_uuid_from_id(self, entity, crmId):
        if not crmId:
            return None
        result = entity.get(id=crmId)
        print("Found "+str(entity)+ ": "+str(result is not None))
        return result.mobile_uuid if result else None