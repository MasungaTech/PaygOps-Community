from datetime import datetime, timedelta
import config
from core_system.operational_entities.services.operational_entities_getter import OperationalEntitiesGetterService

from payg_loan_system.contracts.models.contract_status import ContractStatus

from shared.services.base_getter_service import BaseGetterService
from payg_loan_system.contracts.models.contract_model import Contract
from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService
from core_system.client.services.client_getter_service import ClientGetterService, Client
from core_system.client.services.client_list_service import ClientListService
from core_system.operational_entities.services.client_group_getter_service import ClientGroupGetterService
from decimal import Decimal
from pony import orm
from shared.helpers.db_helpers import searchable_text
from shared.services.settings_service import SettingsService

if config.ENABLE_ENTERPRISE_FEATURES:
    from after_sales_system.issue_system.model.issue_model import Issue, IssueStatus
else:
    Issue = None
    IssueStatus = None


class ContractGetterService(BaseGetterService):

    PK_NAME = 'reference'
    OBJ_NAME = 'Contracts'
    @classmethod
    def preprocess_list_filters(cls, user, **kwargs):
        kwargs['entity'] = OperationalEntitiesGetterService.extract_from_user_and_id(user, kwargs, 'entity_id')
        kwargs['client_group'] = ClientGroupGetterService.extract_from_user_and_id(user, kwargs, 'client_group_id')
        client = ClientGetterService.extract_from_user_and_id(user, kwargs, 'client_id', empty_allowed=True, strict=True)
        if client:
            kwargs['clients'] = [client]
        return kwargs

    @classmethod
    def get_from_filtered_view(cls, user, view=None, status=None, **kwargs):

        if status == 'active':
            kwargs['active'] = True
        elif status == 'defaulted':
            kwargs['defaulted'] = True
        elif status == 'completed':
            kwargs['completed'] = True
        elif status == 'cancelled':
            kwargs['cancelled'] = True
        elif status == 'paused':
            kwargs['paused'] = True
        elif status == 'late':
            kwargs['late'] = True
        elif status == 'overpaid':
            kwargs['overpaid'] = True
        if view == 'managed_by_me':
            kwargs['managed_by'] = user
        elif view == 'generated_by_me':
            kwargs['generated_by'] = user

        return cls.get_list(user, **kwargs)

    @classmethod
    def get_filtered_objects(cls, current_user, active=None, awaiting_payment=None, clients=None,
        entity=None, defaulted=None, completed=None, cancelled=None, paused=None, portfolio=None,
        client_group=None, search=None, min_payment_due=None, max_payment_due=None, min_cumulative_days=None,
        max_cumulative_days=None, managed_by=None, generated_by=None, extra_permission=None, addon_offer=None,
        contract_offer=None, offer_type=None, from_date=None, to_date=None, loan_progress_min=None, overpaid=None,
        loan_progress_max=None, with_issues=None, id=None, tags=None, status=None, delivery_status=None, late=None, from_delivery_date=None, to_delivery_date=None, **kwargs):

        # If the user cant see all contracts or if a entity filter is selected, we filter by entity
        if not current_user.can_access_in_all('ViewClients') or entity:
            allowed_clients = ClientGetterService.get_list(current_user, entity=entity, extra_permission=extra_permission)
            contracts = Contract.select(lambda c: c.client in allowed_clients)
        else:
            contracts = Contract.select()
        if id:
            contracts = contracts.filter(id=id)
        if active:
            contracts = contracts.filter(status=ContractStatus.active)
        if defaulted:
            contracts = contracts.filter(status=ContractStatus.defaulted)
        if completed:
            contracts = contracts.filter(status=ContractStatus.completed)
        if cancelled:
            contracts = contracts.filter(status=ContractStatus.cancelled)
        if paused:
            contracts = contracts.filter(status=ContractStatus.paused)
        if late:
            contracts = contracts.filter(status=ContractStatus.late)
        if overpaid:
            contracts = contracts.filter(status=ContractStatus.overpaid)
        if awaiting_payment:
            awaiting_payment_statuses = [ContractStatus.active,ContractStatus.late]
            if SettingsService.get_setting('AllowPendingPayments'):
                awaiting_payment_statuses.append(ContractStatus.completed)
            if SettingsService.get_setting('AllowPaymentsFromPausedContractsAsPending'):
                awaiting_payment_statuses.append(ContractStatus.paused)
            contracts = contracts.filter(lambda c: c.status in awaiting_payment_statuses)
        if status:
            contracts = contracts.filter(status=status)
        if portfolio:
            contracts = contracts.filter(portfolio=portfolio)
        if client_group:  
            contracts = contracts.filter(lambda c: c.client.person.client_group == client_group)
        if clients:
            contracts = contracts.filter(lambda c: c.client in clients)
        if tags:
            clients = orm.select(c for c in Client)
            clients = ClientListService.filter_by_tags(clients, tags)
            client_ids = orm.select(c.id for c in clients)
            contracts = contracts.filter(lambda c: c.client.id in client_ids)
        if search:
            from core_system.phone_numbers.services.phone_number_getter import PhoneNumberGetterService
            persons = PhoneNumberGetterService.find_persons_if_search_is_number(search)
            devices_contracts_ids = orm.select(d.contract.id for d in DeviceGetterService.get_list(current_user, serial_number=search))[:]
            search = searchable_text(search)
            search_upper = search.upper()
            contracts = contracts.filter(lambda c: 
                search in c.client.person.searchable_name or 
                search_upper == c.reference or 
                search == c.client.person.custom_id or 
                c.id in devices_contracts_ids or 
                c.client.person in persons
            )
        if addon_offer:
            contracts = contracts.filter(lambda c: addon_offer in c.add_ons.offer_version.offer)
        if contract_offer:
            contracts = contracts.filter(lambda c: c.offer == contract_offer)
        if offer_type:
            contracts = contracts.filter(lambda c: c.offer.type == offer_type)
        now = datetime.now()
        if min_payment_due:
            days = timedelta(days=int(min_payment_due))
            contracts = contracts.filter(
                lambda c: (c.next_repayment_due_time-now) >= days
            )
        if max_payment_due:
            max_payment_due = int(max_payment_due) if int(max_payment_due) != 0 else -1
            days = timedelta(days=int(max_payment_due)+1)
            contracts = contracts.filter(
                lambda c: (c.next_repayment_due_time-now) < days
            )
        if min_cumulative_days:
            contracts = contracts.filter(
                lambda c: c.cached_cumulative_days_late >= int(min_cumulative_days)
            )
        if max_cumulative_days:
            contracts = contracts.filter(
                lambda c: c.cached_cumulative_days_late <= int(max_cumulative_days)
            )
        if managed_by:
            clients = ClientGetterService.get_list(current_user, managed_by=managed_by)
            contracts = contracts.filter(lambda c: c.client in clients)

        if generated_by:
            contracts = contracts.filter(lambda c: c.lead.generator == generated_by.person.leadGenerator)
        if from_date:
            contracts = contracts.filter(lambda c: c.start_time >= from_date)
        if to_date:
            contracts = contracts.filter(lambda c: c.start_time <= to_date)
        if loan_progress_min:
            contracts = contracts.filter(lambda c: c.cached_percentage_paid >= Decimal(loan_progress_min)/100)
        if loan_progress_max:
            contracts = contracts.filter(lambda c: c.cached_percentage_paid <= Decimal(loan_progress_max)/100)
        if with_issues is not None and Issue and IssueStatus:
            open_issues = orm.select(i for i in Issue if i.status in IssueStatus.OPEN_ISSUE_STATUSES)
            clients_with_issues = orm.select(c.affectedClient.id for c in open_issues)[:]
            if with_issues in [True, 'true', 'True']:
                contracts = contracts.filter(lambda c: c.client.id in clients_with_issues)
            if with_issues in [False, 'false', 'False']:
                contracts = contracts.filter(lambda c: c.client.id not in clients_with_issues)
        elif with_issues is not None:
            # Ignore issue filters silently when enterprise modules are not available.
            pass

        if delivery_status == 'delivered':
            contracts = contracts.filter(lambda c: not orm.exists(c.add_ons.filter(lambda a: not a.delivered)))
        elif delivery_status == 'partially_delivered':
            contracts = contracts.filter(lambda c: orm.exists(c.add_ons.filter(lambda a: not a.delivered)))
        if from_delivery_date and to_delivery_date:
            contracts = contracts.filter(lambda c: (c.start_time >= from_delivery_date and c.start_time <= to_delivery_date) or orm.exists(c.add_ons.filter(lambda a: a.delivery_date >= from_delivery_date and a.delivery_date <= to_delivery_date)))
        elif from_delivery_date:
            contracts = contracts.filter(lambda c: c.start_time >= from_delivery_date or orm.exists(c.add_ons.filter(lambda a: a.delivery_date >= from_delivery_date)))
        elif to_delivery_date:
            contracts = contracts.filter(lambda c: c.start_time <= to_delivery_date or orm.exists(c.add_ons.filter(lambda a: a.delivery_date <= to_delivery_date)))


        return contracts

    @classmethod
    def get_from_device_code(cls, device_code):
        this_device = DeviceGetterService.get_device_from_registration_code(device_code)
        return this_device.contract

    @classmethod
    def get_from_device_serial(cls, device_serial):
        this_device = DeviceGetterService.get_device_from_serial_number_only(device_serial, raise_if_absent=False)
        return this_device.contract
    
    @classmethod
    def get_list_for_mobile(cls, current_user, cached_ids, **kwargs):
        return current_user.get_relevant_contracts_for_mobile(cached_ids['client'])
