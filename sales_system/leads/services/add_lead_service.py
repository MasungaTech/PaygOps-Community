from datetime import datetime, timedelta

from core_system.operational_entities.services.client_group_getter_service import ClientGroupGetterService
from payg_loan_system.contracts.services.addon_service import AddonService
from payg_loan_system.contracts.services.contract_getter_service import ContractGetterService
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService
from payg_loan_system.offers.services.list_offer_service import ListOfferService
from payg_loan_system.offers.services.offer_entity_restriction_service import OfferEntityRestrictionService
from sales_system.leads.services.lead_error_messages_service import LeadErrorMessagesService
from core_system.client.services.client_getter_service import ClientGetterService
from payg_loan_system.contracts.services.contract_reference_service import ContractReferenceService
from pony.orm import desc

import config
from core_system.client.services.client_getter_service import \
    ClientGetterService
from core_system.core_entities import db
from core_system.operational_entities.models import Village
from core_system.operational_entities.services.client_group_getter_service import \
    ClientGroupGetterService
from core_system.person.models.person_model import Person
from core_system.person.services.edit_person_service import EditPersonService
from core_system.portfolios.services.portfolio_getter_service import PortfolioGetterService
from payg_loan_system.contracts.services.contract_getter_service import \
    ContractGetterService
from payg_loan_system.contracts.services.contract_reference_service import \
    ContractReferenceService
from payg_loan_system.devices.device_api.device_getter_service import \
    DeviceGetterService
from payg_loan_system.offers.services.list_offer_service import \
    ListOfferService
from sales_system.lead_generator.services.lead_generator_getter_service import \
    LeadGeneratorGetterService
from sales_system.leads.models.lead import Lead
from sales_system.leads.models.lead_status import LeadStatus
from sales_system.leads.models.status_category import BILLING_INACTIVE_CATEGORIES, StatusCategory
from sales_system.leads.services.edit_lead_service import EditLeadService
from sales_system.leads.services.lead_error_messages_service import \
    LeadErrorMessagesService
from sales_system.leads.services.lead_status_change_service import \
    LeadStatusChangeService
from sales_system.leads.services.lead_status_service import LeadStatusService
from shared.file_upload.services.stored_file_service import StoredFileService
from shared.api_helpers.hook_helpers.process_hook import add_hook_after_commit
from shared.helpers import date_helper
from shared.helpers.form_helpers import value_to_bool
from shared.logger.loggers import Error
from shared.services.settings_service import SettingsService
from constants import GENDER_IDS
from shared.services.base_service import BaseService
from shared.validators.delivery_date import validate_planned_delivery_dates


class AddLeadService(BaseService):
    PERSON_TYPE_LEAD = 4

    @classmethod
    def _add_from_data_and_user(cls, data, user):
        return cls.add_lead(data, user)

    @classmethod
    def get_human_readable_message(cls, error, user=None):
        return LeadErrorMessagesService.get_human_readable_error(error, user=user)

    @classmethod
    def add_lead(cls, data, user_adding):
        if not user_adding:
            raise Error('USER_ADDING_REQUIRED')
        user_adding = user_adding.reload()
        original_lead = None
        contract_reference = data.get('contract_reference') 
        duplicate_addons_from_contract = None
        if contract_reference:
            contract = ContractGetterService.get_from_user_and_properties(user_adding, reference=contract_reference)
            if contract:
                data['offer_id'] = contract.offer.id
                duplicate_addons_from_contract = contract
                original_lead = contract.lead
                if data.get('name') or data.get('surname') and f"{data['name']} {data['surname']}" != contract.client.person.full_name:
                    raise Error('CLIENT_NAME_DOES_NOT_MATCH')
                if original_lead.status.category == StatusCategory.cancelled:
                    excluded_statuses = [s.name for s in LeadStatusService.get_list(user_adding, categories=[StatusCategory.installed, StatusCategory.cancelled])]
                    status = original_lead.status_changes_history.filter(lambda s: s.status not in excluded_statuses).order_by(lambda s: desc(s.date)).first()
                    status_id = status.status_id.id
                    if not status_id or not LeadStatus.get(id=status_id):
                        status_id = LeadStatusService.get_list(user_adding, categories=[StatusCategory.awaiting_delivery]).first().id
                    client = contract.client
                    data['client'] = client.id
                    data['status'] = status_id
                    data['generator'] = original_lead.generator.id
                    data['generation_date'] = original_lead.receptionTime.strftime("%Y-%m-%d %H:%M")
                    if original_lead.nextContact:
                        data['next_planned_contact'] = original_lead.nextContact.strftime("%Y-%m-%d %H:%M")
                    if original_lead.promisedToPay:
                        data['promised_to_pay_date'] = original_lead.promisedToPay.strftime("%Y-%m-%d %H:%M")
                    if original_lead.agreedDeliveryDate:
                        data['planned_delivery_date'] = original_lead.agreedDeliveryDate.strftime("%Y-%m-%d %H:%M")
                    if original_lead.portfolio:
                        data['portfolio'] = original_lead.portfolio.id
                    if original_lead.commission:
                        data['commission'] = original_lead.commission
                    if original_lead.commissionComment:
                        data['commission_note'] = original_lead.commissionComment

        client = None
        if 'client_mobile' in data:
            client_query = ClientGetterService.get_list(user_adding, for_new_contract=True).filter(lambda c: c.mobile_uuid == data['client_mobile'])
            client = client_query.get() if client_query else None
            if not client:
                raise Error('Client not found')
            person = client.person
        elif 'client' in data and data['client']:
            client = ClientGetterService.get_list(user_adding, for_new_contract=True).filter(lambda c: c.id == data['client']).get()
            if not client:
                raise Error('Client not found')
            person = client.person
        else:
            person = cls._create_person(data, user_adding)

        if not user_adding.can_access('AddLeads', person=person):
            raise Error('INSUFFICIENT_PERMISSION', permission='AddLeads')

        if not SettingsService.get_setting('FeatureToggles').get('SalesFeatures'):
            lead_generator = LeadGeneratorGetterService.get_filtered_objects(
                user_adding, lead_generator_type='Default Lead Generator'
            ).get()
        else:
            if not data.get('generator'):
                raise Error('NO_LEAD_GENERATOR')
            lead_generator = LeadGeneratorGetterService.get_from_user_and_id(
                user_adding, data.get('generator'), strict=True
            )

        allocated_device = None
        if data.get('allocated_device'):
            if not user_adding.can_access('EditAllocatedDeviceLeads', person=person):
                raise Error('INSUFFICIENT_PERMISSION', permission='EditAllocatedDeviceLeads')
            allocated_device = DeviceGetterService.get_from_user_and_properties(user_adding, composed_serial=data["allocated_device"], strict=True)
            if allocated_device.allocated_lead:
                raise Error('DEVICE_ALREADY_ALLOCATED', lead_id=allocated_device.allocated_lead.id)
            if allocated_device.contract:
                raise Error('DEVICE_ALREADY_REGISTERED', device_owner_id=allocated_device.contract.client.id)

        status = data.get('status')
        status = LeadStatusService.get_status(status)
        mobile_uuid = data.get('mobile_uuid', None)
        if not status:
            raise Error('LEAD_STATUS_REQUIRED')
        if status not in LeadStatusService.get_allowed_statuses_for_new_lead(user_adding) and not original_lead and not mobile_uuid:
            raise Error('FORBIDDEN_STATUS_FOR_NEW_LEAD')

        
        portfolio_id = cls.validate_required_fields('portfolio', data.get('portfolio_id', data.get('portfolio')))
        portfolio = PortfolioGetterService.get_from_user_and_id(user_adding, portfolio_id, strict=True) if portfolio_id else None

        commission = data.get('commission')
        if commission:
            try:
                commission = int(commission)
            except Exception as error:
                raise Error('INVALID_COMMISSION_VALUE')

        EditPersonService.check_new_phone_numbers(person, data, required=SettingsService.get_setting('LeadInfoSettings')['phone_number']['required'] and not client)

        entry_date = cls._extract_entry_date(data)
        status_comment = cls.validate_required_fields('comment_on_status', data.get('status_comment', '' if mobile_uuid else ''))
        agreed_delivery_date = date_helper.parse_datetime(data.get('planned_delivery_date'))
        if agreed_delivery_date and not original_lead:
            validate_planned_delivery_dates(agreed_delivery_date, user_adding)
        this_lead = Lead(
            person=person,
            generator=lead_generator,
            receptionTime=date_helper.parse_datetime(data.get('generation_date')) if data.get('generation_date') else datetime.now(),
            status=status,
            status_comment=status_comment,
            statusUpdate=datetime.now(),
            reporter=user_adding,
            entryDate= entry_date or datetime.now(),
            modifiedDate=datetime.now(),
            nextContact=cls.validate_required_fields('next_planned_contact', date_helper.parse_datetime(data.get('next_contact', ''))),
            promisedToPay=date_helper.parse_datetime(data.get('promised_to_pay_date')),
            agreedDeliveryDate=agreed_delivery_date or None,
            portfolio=portfolio,
            commission=commission or 0,
            commissionComment=data.get('commission_note') or '',
            paymentRef="",
            allocated_device=allocated_device.id if allocated_device else None,
            based_on_lead=original_lead,
        )
        this_lead.future_contract_reference = ContractReferenceService.generate_for_lead(this_lead)
        #if it was created on mobile we need to keep the same mobile_uuid
        if mobile_uuid:
            this_lead.mobile_uuid = mobile_uuid
        reasons_for_not_buying = data.get('reasons_for_not_buying')
        EditLeadService.add_reasons_to_lead(this_lead,reasons_for_not_buying)

        # Initialize last_time_active for new leads - all new leads should be counted for billing
        # regardless of their initial status, as they represent a new contact in the system
        current_time = datetime.now()
        this_lead.last_time_active = current_time
        # If the lead is created in an inactive status, also set last_time_inactive
        if status.category in BILLING_INACTIVE_CATEGORIES:
            this_lead.last_time_inactive = current_time

        LeadStatusChangeService.create_status_change_from_lead(this_lead)

        if data.get('offer_id', data.get('offer')):
            this_offer = ListOfferService.get_from_user_and_id(user_adding, data.get('offer_id', data.get('offer')), strict=True)
            if this_lead.allocated_device and not this_lead.allocated_device.can_use_offer(this_offer):
                raise Error('Device not allowed for this offer')
            OfferEntityRestrictionService.assert_offer_allowed_for_lead(
                this_offer, this_lead.person.village
            )
            this_lead.offer = this_offer
        
        if duplicate_addons_from_contract and duplicate_addons_from_contract.add_ons:
            for addon in duplicate_addons_from_contract.add_ons.order_by(lambda a: a.id):
                assert not this_lead.already_paid
                addon_delivery_date = addon.planned_delivery_date if addon.planned_delivery_date else this_lead.agreedDeliveryDate
                AddonService.create(
                    None,
                    addon.offer_version,
                    addon.quantity_sold,
                    user_adding,
                    loan_mode=addon.loan_mode,
                    lead=this_lead,
                    note=addon.note,
                    duplicating=True,
                    planned_delivery_date=addon_delivery_date,
                    device_serial=addon.device.composed_serial if addon.device else None
                )
        EditPersonService.edit_phone_numbers(this_lead.person, data, user_adding)
        # if original_lead:
        #     ReconciliationService.reconcile_pending_payments_to_lead(this_lead, check_status=False)
        LeadStatusChangeService.update(this_lead)

        if data.get('custom_data'):
            EditLeadService._process_custom_data_update(this_lead, data)
        
        if data.get('skip_hook', False) not in [True, 'true']:
            add_hook_after_commit(db, 'lead_added', this_lead.get_serialized_object())
        return this_lead

    @classmethod
    def _create_person(cls, data, user):
        if data.get('village'):
            this_village = Village.get(code=str(data.get('village')))
            if not this_village:
                raise Error('INVALID_VILLAGE_ID')
        elif data.get('l0_entity_id'):
            this_village = Village.get(id=data.get('l0_entity_id'))
            if not this_village:
                raise Error('INVALID_VILLAGE_ID')
        else:
            raise Error('VILLAGE_REQUIRED')

        name = cls.validate_required_fields('first_name', data.get('name', ''))
        surname = cls.validate_required_fields('surname', data.get('surname', ''))
        gender = cls.validate_required_fields('gender', data.get('gender'))
        if gender:
            if isinstance(gender, str):
                gender = GENDER_IDS.get(gender.lower())
            # else gender is already an int ID (e.g. from mobile client data)
        else:
            gender = None
        

        home_use = value_to_bool(data.get('home', False))
        business_use = value_to_bool(data.get('business', False))
        if not home_use and not business_use:
            home_use = True

        sms_language = cls.validate_required_fields('preferred_sms_language', data.get('sms_language', ''))
        if sms_language:
            if sms_language not in config.AVAILABLE_CLIENTS_SMS_LANGUAGES:
                raise Error('INVALID_SMS_LANGUAGE')
        mobile_uuid=data.get('fk_person') if data.get('fk_person') else None

       
        custom_id = data.get('custom_id')
        if custom_id:
            EditPersonService.validate_custom_id(custom_id)

        client_group_id = cls.validate_required_fields('client_group', data.get('client_group_id'))
        client_group = ClientGroupGetterService.get_from_user_and_id(user, client_group_id, strict=True) if client_group_id else None

                

        this_person = Person(
            name=name,
            surname=surname,
            type=cls.PERSON_TYPE_LEAD,
            gender=gender,
            birthdate=date_helper.parse_datetime(data.get('birthdate')) if cls.validate_required_fields('birthdate', data.get('birthdate', '')) else None,
            GPSLon= cls.validate_required_fields('gps_coordinates', data.get('gps_longitude')) or None,
            GPSLat= cls.validate_required_fields('gps_coordinates', data.get('gps_latitude')) or None,
            village=this_village,
            homeUse=home_use,
            businessUse=business_use,
            verbal_language=cls.validate_required_fields('verbal_language', data.get('verbal_language', '')),
            sms_language=sms_language if sms_language else '',
            custom_id=custom_id or None,
            client_group=client_group

        )

        if mobile_uuid:
            this_person.mobile_uuid = mobile_uuid

        picture_uuid = cls.validate_required_fields('profile_picture', data.get('picture_id', ''))
        if picture_uuid:
            this_picture = StoredFileService.get_from_uuid(picture_uuid)
            if this_picture:
                this_person.profile_picture = this_picture
            else:
                this_picture = StoredFileService.create_without_file(type=None, uuid=picture_uuid)
                this_person.profile_picture = this_picture
        get_gps_from_picture = data.get('get_gps_from_picture', '')
        if get_gps_from_picture:
            this_picture = this_person.profile_picture
            if this_picture and this_picture.available:
                if this_picture.picture_gpslon and this_picture.picture_gpslat:
                    this_person.GPSLat = this_picture.picture_gpslat
                    this_person.GPSLon = this_picture.picture_gpslon

        return this_person

    @classmethod
    def _extract_entry_date(cls, data):
        entry_timestamp = data.get('entry_date')

        if not entry_timestamp:
            return None

        return cls._to_datetime(entry_timestamp)

    @classmethod
    def _to_datetime(cls, datetime_as_string):
        return date_helper.formatDateStringToDate(datetime_as_string)

    @classmethod
    def get_affected_entity(cls, data, user, **kwargs):
        entity = None
        if data.get('client_group_id'):
            entity = ClientGroupGetterService.get_from_user_and_id(user, data.get('client_group_id'), strict=True)
        if data.get('village'):
            entity = Village.get(code=str(data.get('village')))
            if not entity:
                raise Error('INVALID_VILLAGE_ID')
        if data.get('l0_entity_id'):
            entity = Village.get(id=data.get('l0_entity_id'))
            if not entity:
                raise Error('INVALID_L0_ENTITY_ID')
        if data.get('contract_reference'):
            contract = ContractGetterService.get_from_user_and_properties(user, reference=data.get('contract_reference'))
            if contract:
                data['client'] = contract.client.id
        if data.get('client'):
            client = ClientGetterService.get_list(user, for_new_contract=True).filter(lambda c: c.id == data['client']).get()
            if not client:
                raise Error('Client not found')
            entity = client.person.village
        if not entity:
            raise Error('VILLAGE_REQUIRED', code='VILLAGE_REQUIRED')
        return entity

    @classmethod
    def validate_required_fields(cls, field_name, value):
        personal_info_settings_obj = SettingsService.get_setting('LeadInfoSettings')
        if personal_info_settings_obj[field_name]['required'] and not value:
            raise Error(f"{field_name} is a required field")
        return value