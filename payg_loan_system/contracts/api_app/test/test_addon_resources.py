from datetime import datetime, timedelta
from payg_loan_system.contracts.models.addon_category import AddOnCategory
from pony.orm import db_session
from payg_loan_system.contracts.services.addon_service import AddonService, ContractAddOn
from payg_loan_system.contracts.services.addons.addon_offer_service import AddonOfferService, AddOnType
from shared.helpers.client_creator import ClientCreator
from shared.api_helpers.client_helpers.json_serialization_helpers import serialize_data_to_json, deserialize_json_data
import json
from core_system.users.services.user_getter_service import UserGetterService
from config import API_PREFIX


class TestAddonResource:

    def test_get_addon_resource(self, api_client, good_api_key, admin_api_key):

        response = api_client.get(
            API_PREFIX + '/addons/NON-EXISTING-REFERENCE',
            headers={'Authorization': 'Bearer ' + good_api_key}
        )
        assert response.status_code == 404

        response = api_client.get(
            API_PREFIX + '/addons/NON-EXISTING-REFERENCE',
            headers={'Authorization': 'Bearer ' + admin_api_key}
        )
        assert response.status_code == 404

        with db_session:
            user = UserGetterService.get_by_username("super_admin@test.com")
            contract = ClientCreator.create(api_client, good_api_key).contracts.select().first()

            offer = AddonOfferService.create(
                user,
                "OFFER 1",
                "OFFERTOTESTADDONS_API",
                "1",
                AddOnCategory.get(name="Product"),
                AddOnType.lump_sum,
                available=True
            )

            addon = AddonService.create(contract, offer.last_version, 1, user)

        response = api_client.get(
            API_PREFIX + '/addons/'+addon.reference,
            headers={'Authorization': 'Bearer ' + admin_api_key}
        )
        assert response.status_code == 200
        self._check_object(response, addon)


    def test_patch_addon_resource(self, api_client, api_key_bad_permissions, good_api_key, admin_api_key):

        response = api_client.patch(
            API_PREFIX + '/addons/NON-EXISTING-REFERENCE',
            json={},
            headers={'Authorization': 'Bearer ' + api_key_bad_permissions}
        )
        assert response.status_code == 403

        response = api_client.patch(
            API_PREFIX + '/addons/NON-EXISTING-REFERENCE',
            json={},
            headers={'Authorization': 'Bearer ' + admin_api_key}
        )
        assert response.status_code == 404

        with db_session:
            user = UserGetterService.get_by_username("super_admin@test.com")
            contract = ClientCreator.create(api_client, good_api_key).contracts.select().first()

            offer = AddonOfferService.create(
                user,
                "OFFER 1",
                "OFFERTOTESTADDONS_API2",
                "1",
                AddOnCategory.get(name="Product"),
                AddOnType.lump_sum,
                need_approval=True,
                available=True
            )

            addon = AddonService.create(contract, offer.last_version, 1, user)

        response = api_client.patch(
            API_PREFIX + '/addons/'+addon.reference,
            json={'approved_by': None},
            headers={'Authorization': 'Bearer ' + admin_api_key}
        )
        assert response.status_code == 400

        response = api_client.patch(
            API_PREFIX + '/addons/'+addon.reference,
            json={'approved': True},
            headers={'Authorization': 'Bearer ' + admin_api_key}
        )
        assert response.status_code == 200
        self._check_object(response, addon)

        response = api_client.patch(
            API_PREFIX + '/addons/'+addon.reference,
            json={'cancelled': True},
            headers={'Authorization': 'Bearer ' + admin_api_key}
        )
        assert response.status_code == 200
        self._check_object(response, addon)

        with db_session:
            ContractAddOn.get(id=addon.id).time_canceled = None

        response = api_client.patch(
            API_PREFIX + '/addons/'+addon.reference,
            json={'cash_collection_agent': None},
            headers={'Authorization': 'Bearer ' + admin_api_key}
        )
        assert response.status_code == 400

        response = api_client.patch(
            API_PREFIX + '/addons/'+addon.reference,
            json={'cash_collection_agent': user.id},
            headers={'Authorization': 'Bearer ' + admin_api_key}
        )
        assert response.status_code == 200
        self._check_object(response, addon)

    def test_batch_patch_addon_resource(self, api_client, api_key_bad_permissions, good_api_key, admin_api_key):

        response = api_client.patch(
            API_PREFIX + '/addons',
            json=[{"id": None}],
            headers={'Authorization': 'Bearer ' + api_key_bad_permissions}
        )
        assert response.status_code == 403

        response = api_client.patch(
            API_PREFIX + '/addons',
            json=[{"id": None}],
            headers={'Authorization': 'Bearer ' + admin_api_key}
        )
        assert response.status_code == 404

        with db_session:
            user = UserGetterService.get_by_username("super_admin@test.com")
            contract = ClientCreator.create(api_client, good_api_key).contracts.select().first()

            offer = AddonOfferService.create(
                user,
                "OFFER 1",
                "OFFERTOTESTADDONS_API3",
                "1",
                AddOnCategory.get(name="Product"),
                AddOnType.lump_sum,
                need_approval=True,
                available=True
            )

            addon = AddonService.create(contract, offer.last_version, 1, user)

        response = api_client.patch(
            API_PREFIX + '/addons',
            json=[{'id': addon.id, 'lead_id': 35}],
            headers={'Authorization': 'Bearer ' + admin_api_key}
        )
        assert response.status_code == 400

        response = api_client.patch(
            API_PREFIX + '/addons',
            json=[{'id': addon.id, 'approved_by': user.id}],
            headers={'Authorization': 'Bearer ' + admin_api_key}
        )
        assert response.status_code == 200
        assert response.json['success']
        assert f'edited successfully: [{addon.id}]' in response.json['message']

        response = api_client.patch(
            API_PREFIX + '/addons',
            json=[{'id': addon.id, 'cancelled': True}],
            headers={'Authorization': 'Bearer ' + admin_api_key}
        )
        assert response.status_code == 200
        assert response.json['success']
        assert f'edited successfully: [{addon.id}]' in response.json['message']

        with db_session:
            ContractAddOn.get(id=addon.id).time_canceled = None

        response = api_client.patch(
            API_PREFIX + '/addons',
            json=[{'id': addon.id, 'cash_collection_agent': None}],
            headers={'Authorization': 'Bearer ' + admin_api_key}
        )
        assert response.status_code == 400

        response = api_client.patch(
            API_PREFIX + '/addons',
            json=[{'id': addon.id, 'cash_collection_agent': user.id}],
            headers={'Authorization': 'Bearer ' + admin_api_key}
        )
        assert response.status_code == 200
        assert response.json['success']
        assert f'edited successfully: [{addon.id}]' in response.json['message']

    def test_patch_addon_all_editable_parameters(self, api_client, good_api_key, admin_api_key):
        addon = self._create_pending_addon(api_client, good_api_key, 'PATCHALL_NOTE', note='')
        response = api_client.patch(
            API_PREFIX + '/addons/' + addon.reference,
            json={'note': 'updated from automation'},
            headers={'Authorization': 'Bearer ' + admin_api_key}
        )
        assert response.status_code == 200
        assert response.json['note'] == 'updated from automation'
        assert response.json['approved'] is False
        assert response.json['delivered'] is False

        planned = (datetime.now() + timedelta(days=2)).replace(microsecond=0)
        response = api_client.patch(
            API_PREFIX + '/addons/' + addon.reference,
            json={'planned_delivery_date': planned.isoformat()},
            headers={'Authorization': 'Bearer ' + admin_api_key}
        )
        assert response.status_code == 200
        assert response.json['planned_delivery_date']
        assert response.json['planned_delivery_date'].startswith(planned.date().isoformat())

        response = api_client.patch(
            API_PREFIX + '/addons/' + addon.reference,
            json={'quantity_sold': 2},
            headers={'Authorization': 'Bearer ' + admin_api_key}
        )
        assert response.status_code == 200
        assert response.json['quantity_sold'] == 2.0

        addon_to_approve = self._create_pending_addon(api_client, good_api_key, 'PATCHALL_APPROVE')
        response = api_client.patch(
            API_PREFIX + '/addons/' + addon_to_approve.reference,
            json={'approved': True, 'delivered': True, 'note': 'approved and delivered'},
            headers={'Authorization': 'Bearer ' + admin_api_key}
        )
        assert response.status_code == 200
        assert response.json['approved'] is True
        assert response.json['approved_by'] is not None
        assert response.json['delivered'] is True
        assert response.json['note'] == 'approved and delivered'

        response = api_client.patch(
            API_PREFIX + '/addons/' + addon_to_approve.reference,
            json={'delivered': False},
            headers={'Authorization': 'Bearer ' + admin_api_key}
        )
        assert response.status_code == 200
        assert response.json['delivered'] is False
        assert response.json['approved'] is True

        addon_to_cancel = self._create_pending_addon(api_client, good_api_key, 'PATCHALL_CANCEL')
        response = api_client.patch(
            API_PREFIX + '/addons/' + addon_to_cancel.reference,
            json={'cancelled': True},
            headers={'Authorization': 'Bearer ' + admin_api_key}
        )
        assert response.status_code == 200
        assert response.json['cancelled'] is True

        first_offer_addon = self._create_pending_addon(api_client, good_api_key, 'PATCHALL_OFFER_A')
        with db_session:
            user = UserGetterService.get_by_username("super_admin@test.com")
            replacement_offer = AddonOfferService.create(
                user,
                "PATCH ALL OFFER B",
                "PATCHALL_OFFER_B",
                "5",
                AddOnCategory.get(name="Product"),
                AddOnType.lump_sum,
                need_approval=True,
                available=True
            )
            replacement_version_id = replacement_offer.last_version.id
            replacement_code = replacement_offer.code
        response = api_client.patch(
            API_PREFIX + '/addons/' + first_offer_addon.reference,
            json={'offer_code': replacement_code},
            headers={'Authorization': 'Bearer ' + admin_api_key}
        )
        assert response.status_code == 200
        assert response.json['offer_code'] == replacement_code

        other_offer_addon = self._create_pending_addon(api_client, good_api_key, 'PATCHALL_OFFER_C')
        response = api_client.patch(
            API_PREFIX + '/addons/' + other_offer_addon.reference,
            json={'offer_version_id': replacement_version_id},
            headers={'Authorization': 'Bearer ' + admin_api_key}
        )
        assert response.status_code == 200
        assert response.json['offer_version_id'] == replacement_version_id

    @staticmethod
    def _create_pending_addon(api_client, good_api_key, offer_code, note=''):
        with db_session:
            user = UserGetterService.get_by_username("super_admin@test.com")
            contract = ClientCreator.create(api_client, good_api_key).contracts.select().first()
            offer = AddonOfferService.create(
                user,
                offer_code,
                offer_code,
                "1",
                AddOnCategory.get(name="Product"),
                AddOnType.lump_sum,
                need_approval=True,
                available=True
            )
            return AddonService.create(contract, offer.last_version, 1, user, note=note)

    @staticmethod
    @db_session
    def _check_object(response, addon):
        serialized = ContractAddOn.get(id=addon.id).get_serialized_object()
        # Step below required to properly compare dates
        serialized = json.loads(serialize_data_to_json(serialized))
        for key, value in serialized.items():
            if '_date' in key and serialized[key]:
                serialized[key] = serialized[key] = serialized[key]+'Z'
        assert response.json == serialized
