from payg_loan_system.devices.device_api.device_getter_service import DeviceGetterService
from payg_loan_system.contracts.services.contract_getter_service import ContractGetterService
from core_system.users.services.current_user_service import get_current_api_user
from flask_restful import Resource, request
from shared.api_helpers.server_helpers.jwt_and_schema_verification import verify
from pony.orm import db_session, select
from core_system.client.models import Client
from core_system.person.models.person_model import Person
from core_system.phone_numbers.services.phone_number_getter import PhoneNumberGetterService
from core_system.client.services.client_getter_service import ClientGetterService
from shared.logger.loggers import LogAPI

log_api = LogAPI()


class ClientSimpleResource(Resource):
    @verify(permissions=['ViewClients'])
    @db_session
    def get(self):
        phone_number = request.args.get('phone_number', None)
        client_id = request.args.get('client_id', None)
        contract_reference = request.args.get('contract_reference', None)
        device_serial_number = request.args.get('device_serial_number', None)

        if client_id and client_id != '{{client_id}}':
            client = ClientGetterService.get_from_user_and_id(get_current_api_user(), client_id)
        elif phone_number:
            client = PhoneNumberGetterService.get_client_by_phone_number(phone_number)
        elif contract_reference:
            contract = ContractGetterService.get_from_user_and_properties(get_current_api_user(), reference=contract_reference)
            client = contract.client if contract else None
        elif device_serial_number:
            device = DeviceGetterService.get_device_from_serial_number_only(device_serial_number, raise_if_absent=False)
            client = device.contract.client if device and device.contract else None
        else:
            client = None

        if client:
            if client.person.village:
                village = client.person.village.name
                cluster = client.person.village.parent.name
                hub = client.person.village.parent.parent.name
            else:
                village = None
                cluster = None
                hub = None
            client_dict = {
                'client_id': client.id,
                'client_name': client.person.name,
                'client_surname':client.person.surname,
                'client_village_name': village,
                'client_cluster_name': cluster,
                'client_shop_name': hub,
                'client_registration_date': client.RegistrationDate,
                'client_termination_date': client.termination_date,
                'client_planned_termination_date': client.termination_date,
                'client_birthdate': client.person.birthdate,
                'client_devices': [d.composed_serial for d in list(client.contracts.linked_device)],
                'client_contracts': [contract.reference for contract in list(client.contracts)],
                'client_next_payment_due': client.get_earliest_payment_due(),
                'client_preferred_phone_number': getattr(client.person.contactPhone, 'number', None),
                'client_phone_numbers': [p.number for p in list(client.person.phoneNumbers.copy())]
            }
        else:
            client_dict = {}

        return client_dict, 200


class ClientSimpleListResource(Resource):

    @verify(permissions=['ViewClients'])
    @db_session
    def get(self):
        client_id = request.args.get('client_id', None)
        if client_id and client_id != '{{client_id}}':
            clients = [ClientGetterService.get_from_user_and_id(get_current_api_user(), client_id, strict=True)]
        else:
            clients = ClientGetterService.get_list(get_current_api_user())

        result = [{'client_id': client.id,
                   'client_name': client.person.name,
                   'client_surname':client.person.surname,
                   'client_village_name': client.person.village.name if client.person.village else None,
                   'client_cluster_name': client.person.village.parent.name if client.person.village and client.person.village.parent else None,
                   'client_shop_name': client.person.village.parent.parent.name if client.person.village and client.person.village.parent else None,
                   'client_registration_date': client.RegistrationDate,
                   'client_termination_date': client.termination_date,
                   'client_planned_termination_date': client.termination_date,
                   'client_birthdate': client.person.birthdate,
                   'client_next_payment_due': client.get_earliest_payment_due(),
                   'client_preferred_phone_number': client.person.contactPhone.number if client.person.contactPhone else None,
                   } for client in clients]

        return result, 200
