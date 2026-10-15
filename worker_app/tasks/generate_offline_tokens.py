from pony.orm import db_session
from worker_app.worker_app import worker_app
from core_system.core_entities import db
from payg_loan_system.devices.services.offline_token_service import OfflineTokenService


@worker_app.task
@db_session
def refresh_offline_tokens_for_device(device_id):
    device = db.Device.get(id=device_id)
    if device:
        OfflineTokenService.generate_for_device_if_needed(device)


@worker_app.task
@db_session
def refresh_offline_tokens_for_applicable_devices(offer_id=None, device_type=None):
    offer = None
    if offer_id:
        offer = db.Offer.get(id=offer_id)
    OfflineTokenService.generate_tokens_for_applicable_devices(offer=offer, device_type=device_type)
