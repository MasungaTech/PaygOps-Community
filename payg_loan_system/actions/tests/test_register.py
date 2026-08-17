import pytest
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from payg_loan_system.actions.registration import register_lead
from payg_loan_system.contracts.models.addon_category import AddOnCategory
from payg_loan_system.contracts.services.addon_service import AddonService
from payg_loan_system.contracts.services.addons.addon_offer_service import (
    AddonOfferService, AddOnLoanExtensionMode, AddOnType)
from payg_loan_system.devices.model.product_sub_type import ProductSubType
from stock_management_system.quantity_stock_models import QuantityStockLocation
from stock_management_system.stock_status import StockStatus
from payg_loan_system.devices.services.create_device_service import DeviceCreateService
from pony.orm import db_session, rollback
from payg_loan_system.offers.services.edit_offer_service import EditOfferService
from sales_system.lead_generator.model import LeadGenerator
from sales_system.leads.services.add_lead_service import AddLeadService
from shared.helpers.client_creator import ClientCreator
from shared.logger.loggers import Error
from tests.factories.factories import AbstractUserFactory
from payg_loan_system.devices.factories import DeviceAbstractFactory
from sales_system.leads.tests.factories import AbstractLeadFactory


class TestRegistration:

    @db_session 
    def test_user_without_auth(self, *args):
        user = AbstractUserFactory.create(authorized=False)
        lead = AbstractLeadFactory.create_no_client()
        device = DeviceAbstractFactory.create_no_client()

        resp = register_lead(user, lead, device)

        assert resp == [{'success': False,
                        'status': 'INSUFFICIENT_PERMISSION',
                        'permission': 'RegisterActions'}]

    @db_session
    def test_lead_already_registered(self, super_admin_user, api_client, good_api_key, *args):
        user = super_admin_user()
        lead = ClientCreator.create(api_client, good_api_key).contracts.select().first().lead
        device =  DeviceCreateService.create('TEST1234PER', 'NPG', 1) # DeviceAbstractFactory.create_no_client()

        with pytest.raises(Error) as error:
            resp = register_lead(user, lead, device)

        assert error.value.code == 'LEAD_ALREADY_REGISTERED'
        assert error.value.data == {'client_id': lead.person.client.id}
        rollback()

    @db_session
    def test_lead_not_approved(self, super_admin_user, *args):
        user = super_admin_user()
        data = {
            "village": OperationalEntitiesGetterService.get_list(user, level=0).first().not_empty_code,
            "name": "TestRegistration",
            "surname": "WWW",
            "generator": LeadGenerator.select().first().id,
            "status": 9,
            "gender": "Male",
            "offer": None,
            "preferred_phone_number": "+2340067891235"
        }
        lead = AddLeadService.add_from_data_and_user(data, user)

        # lead = AbstractLeadFactory.create_no_client(no_offer=True)
        # lead.decision = False
        device = DeviceCreateService.create('TESTDEVICEPERM45', 'NPG', 1) #DeviceAbstractFactory.create_no_client()

        with pytest.raises(Error) as error:
            resp = register_lead(user, lead, device)
        assert error.value.code == 'LEAD_NOT_APPROVED'
        rollback()


    @db_session
    def test_lead_awaiting_payment(self, super_admin_user, *args):
        user = super_admin_user()
        lead = ClientCreator.create_lead()
        device = DeviceCreateService.create('TESTDEVICENOTPAID', 'NPG', 1) #DeviceAbstractFactory.create_no_client()

        with pytest.raises(Error) as error:
            resp = register_lead(user, lead, device)
        assert error.value.code == 'LEAD_INITIAL_PAYMENT_NOT_PAID'
        rollback()

    @db_session
    def test_offer_disabled(self, super_admin_user,  api_client, good_api_key, *args):
        user = super_admin_user()
        lead = ClientCreator.create_lead(offer_data={'code': 'NEW_OFFER_TO_DISABLE'})
        ClientCreator.pay_deposit_for_lead(api_client, good_api_key, lead)
        EditOfferService.edit_from_data_and_user(lead.offer, {'can_be_approved_and_registered': False}, super_admin_user())
        device = DeviceCreateService.create("TEST12334345", "NPG", 1) #DeviceAbstractFactory.create_no_client()

        with pytest.raises(Error) as error:
            resp = register_lead(user, lead, device)
        assert error.value.code == 'OFFER_DISABLED'
        rollback()

    @db_session
    def test_delivered_non_serialized_addon_without_device_not_blocked(
        self, api_client, good_api_key, super_admin_user, *args
    ):
        user = super_admin_user()
        lead = ClientCreator.create_lead()

        product = ProductSubType(
            name='Non-serialized mineral block test',
            sku='min-block-test-reg',
            device_type='NPG',
            is_serialized=False,
        )
        QuantityStockLocation(
            product_sub_type=product,
            status=StockStatus.orphaned,
            total_quantity=10,
        )
        offer = AddonOfferService.create(
            user,
            'Non-serialized addon registration test',
            'NONSERADDONREG',
            '10',
            AddOnCategory.get(name='Product'),
            AddOnType.loan,
            available=True,
            loan_mode=AddOnLoanExtensionMode.duration,
            downpayment='3',
            linked_to_product=True,
            product_sub_type_id=product.id,
        )
        addon = AddonService.create(None, offer.last_version, 1, user, lead=lead)
        ClientCreator.pay_deposit_for_lead(api_client, good_api_key, lead)
        lead.offer_editing_locked = True
        device = DeviceCreateService.create('TESTNONSERADDON', 'NPG', 1)

        resp = register_lead(user, lead, device, delivered_addons=[addon])

        assert resp[0]['status'] != 'ADDON_HAS_NO_DEVICE_AND_IS_LINKED_TO_PRODUCT'
        rollback()

