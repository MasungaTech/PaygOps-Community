from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from payg_loan_system.offers.services.list_offer_service import ListOfferService
from sales_system.leads.models.lead import Lead
from pony.orm import flush, commit
from core_system.users.services.user_getter_service import UserGetterService
from payg_loan_system.offers.services.create_offer_service import CreateOfferService
from payg_loan_system.devices.services.create_device_service import DeviceCreateService
from payg_loan_system.actions.registration import register_lead
from sales_system.leads.services.add_lead_service import AddLeadService
from sales_system.leads.services.edit_lead_service import EditLeadService
from sales_system.lead_generator.model import LeadGenerator
from sales_system.leads.models.lead_status import LeadStatus
from sales_system.leads.models.status_category import StatusCategory
from config import API_PREFIX


class ClientCreator:

    offer_data = {
        "code": "ADDONS_TEST_OFFER2",
        "name": "ADDONS TEST OFFER",
        "type": "Loan",
        "downpayment": 10,
        "time_to_ownership_in_days": 365,
        "time_given_at_start_in_days": 0,
        "base_price_amount": 1,
        "raw_unit_cost": '',
        "family": 'Home',
        "base_price_time_in_days": 1,
        "automatic_unlock_code_sending": "True",
        "in_use_for_new_leads": "True",
        "can_be_approved_and_registered": "True"
    }

    phone = "+2344567891235"

    lead_data = {
        "name": "Test",
        "surname": phone,
        "status": 9,
        "preferred_phone_number": phone,
        "gender": "Male"
    }

    device_data = {
        "serial_number": "T"+phone.replace('+', ''),
        "device_type": '1WY',
        "mode": 1
    }

    @classmethod
    def create(cls, api_client, good_api_key, offer_data=None, lead_data=None, device_data=None, extra_paid=0):

        lead = cls.create_lead(offer_data, lead_data)
        client = cls.register_lead(api_client, good_api_key, lead, device_data, extra_paid=extra_paid)
        return client

    @classmethod
    def create_lead(cls, offer_data=None, lead_data=None):
        user = UserGetterService.get_by_username("super_admin@test.com")
        offer_data = cls._subs(cls.offer_data, offer_data)
        offer = ListOfferService.get_from_user_and_properties(user, code=offer_data['code'])
        if not offer:
            offer = CreateOfferService.add_from_data_and_user(offer_data, user)
        if not getattr(user.person, 'leadGenerator'):
            generator = LeadGenerator(person=user.person, type=2)
        else:
            generator = user.person.leadGenerator
        flush()
        cls._update_phone()
        village = OperationalEntitiesGetterService.get_list(user, level=0).first()
        assert village
        cls.lead_data.update({
            "l0_entity_id": village.id,
            "surname": cls.phone,
            "generator": generator.id,
            "offer": offer.id,
            "preferred_phone_number": cls.phone
        })
        commit()
        lead_data = cls._subs(cls.lead_data, lead_data)
        lead = AddLeadService.add_lead(lead_data, user)
        if not lead.deposit_paid:
            EditLeadService.edit_lead(lead, {
                "status": LeadStatus.get_first(StatusCategory.awaiting_payment).id,
            }, user)
        return lead

    @classmethod
    def register_lead(cls, api_client, good_api_key, lead, device_data=None, extra_paid=0):
        user = UserGetterService.get_by_username("super_admin@test.com")
        cls.pay_deposit_for_lead(api_client, good_api_key, lead, extra_paid)
        lead = Lead.get(id=lead.id)
        # in some cases flush is not enough to update properties changed in the api_client
        device = cls.create_device(device_data)
        answer = register_lead(user, lead, device)
        assert lead.contract, "Error creating contract: "+answer[0]['status']
        return lead.contract.client

    @classmethod
    def create_device(cls, device_data=None):
        cls.device_data.update({"serial_number": "T"+cls.phone.replace('+', '')})
        device_data = cls._subs(cls.device_data, device_data)
        return DeviceCreateService.create(**device_data)

    @classmethod
    def pay_deposit_for_lead(cls, api_client, good_api_key, lead, extra_paid=0):
        if not lead.deposit_paid and lead.offer.registration_fee+extra_paid > 0:
            resp = cls.post_payment({
                "transaction_id": "DownPayment"+lead.full_name+str(extra_paid),
                "sender_name": lead.full_name,
                "sender_msisdn": cls.phone,
                "amount": str(lead.offer.registration_fee+extra_paid)
            }, api_client, good_api_key)
            assert resp.status_code == 201, 'Status: ' + str(resp.status) + ' - ' + str(resp.get_json())
            flush()

    @classmethod
    def post_payment(cls, data, api_client, good_api_key):
        response = api_client.post(API_PREFIX + '/payments',
                                   json=data,
                                   headers={'Authorization': 'Bearer ' + good_api_key})
        return response

    @classmethod
    def _update_phone(cls):
        cls.phone = '+' + str(int(cls.phone[1:])+1)

    @staticmethod
    def _subs(base, mod):
        copy = base.copy()
        if mod:
            copy.update(mod)
        return copy
