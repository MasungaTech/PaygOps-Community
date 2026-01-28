from datetime import datetime
from decimal import Decimal
import json
from munch import DefaultMunch
from core_system.client.services.client_edit_service import ClientEditService
from core_system.client.services.client_getter_service import ClientGetterService
from core_system.operational_entities.models import ClientGroup, OperationalEntity
from core_system.operational_entities.services.edit_client_group_service import EditClientGroupService
from core_system.operational_entities.services.edit_operational_entity_service import EditOperationalEntityService
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService
from core_system.users.models.user_model import User
from core_system.users.services.edit_user_service import EditUserService
from payg_loan_system.contracts.api_app.addons_resources import IndividualAddonResource
from payg_loan_system.devices.non_payg_device_service import NonPAYGDeviceService
from payg_loan_system.payments.api_views.reconcile_payment_route import ReconciledPaymentAllResource
from payg_loan_system.payments.services.manual_payment_add_service import ManualPaymentEntryService
from pony.orm import db_session, select
from payg_loan_system.reversed_payments.api_views import PaymentReversalResource
from payg_loan_system.transaction_requests.api_views.transaction_resource import TransactionResource
from payg_loan_system.transaction_requests.services.get_transaction_request_service import GetTransactionRequestService
from sales_system.lead_generator.services.lead_generator_edit_service import LeadGeneratorEditService
from sales_system.leads.services.edit_lead_service import EditLeadService
from sales_system.leads.services.lead_getter_service import LeadGetterService
from shared.api_helpers.api_structure import API_STRUCTURE_NAMES
from shared.api_helpers.base_api_class_all import BaseAPIResourceAll
from shared.api_helpers.base_api_class_individual import BaseAPIResourceIndividual
from shared.logger.loggers import Error
from stock_management_system.services.stock_movement_creation_service import StockMovementCreationService


class BulkUploadTaskProcessors:

    @classmethod
    @db_session
    def payments(cls, payment, task_service):
        user = User.get(id=task_service.user)
        ManualPaymentEntryService.add_manual_payment(
            current_user=user,
            user_ip=task_service.user_ip,
            user_agent=task_service.user_agent,
            request=DefaultMunch(), # It's required so we can't leave it empty
            amount=Decimal(payment[2]),
            reference=payment[0],
            reception_time=payment[1],
            account_name=payment[3],
            account_msisdn=payment[4],
            memo=payment[5],
            wallet_operator=payment[6]
        )

    @classmethod
    @db_session
    def stock_movements(cls, data, task_service):
        user = User.get(id=task_service.user)
        StockMovementCreationService.add_from_data_and_user(data=data, user=user)

    @classmethod
    @db_session
    def devices(cls, device_data, task_service):
        NonPAYGDeviceService.create_non_payg_device(device_data[0], device_data[1])

    @classmethod
    @db_session
    def operational_entities(cls, entity, task_service):
        user = User.get(id=task_service.user)
        if entity[4]:
            parent = OperationalEntitiesGetterService.get_from_user_and_properties(
                user, name=entity[4], level=4
            )
        else:
            parent = OperationalEntitiesGetterService.get_from_user_and_properties(user, level=4)
        ln = 4

        if parent:
            level_names = entity[3::-1]
            for level_name in level_names:
                ln -= 1
                if level_name:
                    child = parent.children.filter(lambda c: c.name == level_name).first()
                else:
                    child = parent.children.select().get()
                if child:
                    parent = child
                else:
                    name = level_name
                    break
        else:
            name = entity[4]
        user_in_charge = User.get(id=entity[5]) if entity[5] else None

        gps_lat, gps_lon, admin_name, admin_number, population, description = entity[6:]
        EditOperationalEntityService.add_from_data_and_user({
            'name': name,
            'level': ln,
            'parent_id': parent.id if parent else None,
            'user_in_charge_id': user_in_charge.id if user_in_charge else None,
            'gps_latitude': gps_lat,
            'gps_longitude': gps_lon,
            'admin_contact_name': admin_name,
            'admin_phone_number': admin_number,
            'population': population,
            'description': description
        }, user)

    @classmethod
    @db_session
    def users(cls, user_data, task_service):
        user = User.get(id=task_service.user)
        EditUserService.edit_user_from_data(user, user_data)

    @classmethod
    @db_session
    def lead_generators(cls, data, task_service):
        user = User.get(id=task_service.user)
        LeadGeneratorEditService.add_from_data_and_user(data, user)

    @classmethod
    @db_session
    def client_groups(cls, group_data, task_service):
        user = User.get(id=task_service.user)
        group = ClientGroup.get(id=group_data.get('client_group_id'))
        EditClientGroupService.edit_from_data_and_user(group, group_data, user)

    @classmethod
    @db_session
    def edit_leads(cls, data, task_service):
        user = User.get(id=task_service.user)
        lead = LeadGetterService.get_from_user_and_id(user, data[0], strict=True)
        EditLeadService.edit_from_data_and_user(lead, data[1], user)

    @classmethod
    @db_session
    def edit_clients(cls, data, task_service):
        user = User.get(id=task_service.user)
        client = ClientGetterService.get_from_user_and_id(user, data[0], strict=True)
        ClientEditService.edit_from_data_and_user(client, data[1], user)

    @classmethod
    @db_session
    def api_caller(cls, data, task_service):
        user = User.get(id=task_service.user)
        resource_name, method = task_service.action.split(':')[0].split('_')
        resource = API_STRUCTURE_NAMES.get(resource_name)

        params, body, _ = data

        if issubclass(resource, ReconciledPaymentAllResource):
            if method == "post":
                return ReconciledPaymentAllResource.post_core(body, user)
        elif issubclass(resource, BaseAPIResourceIndividual):
            if method == 'post':
                return resource.core_post(user, params, body)
            elif method == 'delete':
                return resource.core_delete(user, params)
        elif issubclass(resource, BaseAPIResourceAll):
            if method == 'post':
                return resource.core_post(user, params, body)
        elif issubclass(resource, TransactionResource):
            if method == 'post':
                if GetTransactionRequestService.get_transaction(params['uuid']):
                    raise Error('Transaction already in the system')
                result = resource.post_core(user, params['uuid'], body)
                if not result['success']:
                    raise Error(result['human_answer'] + ' Affected data: '+json.dumps(body))
                return result
            elif method == 'put':
                return resource.put_core(user, params['uuid'], body)
        elif issubclass(resource, IndividualAddonResource):
            if method == 'patch':
                return resource.patch_core(params['reference'], user, body)
        elif issubclass(resource, PaymentReversalResource):
            if method == "post":
                return PaymentReversalResource.post_core(body, user)
        raise Exception('Action execution not defined')
    
