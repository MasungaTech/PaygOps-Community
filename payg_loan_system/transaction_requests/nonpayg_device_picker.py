from constants import NON_PAYG_TYPE
from shared.services.settings_service import SettingsService


def should_show_auto_generated_nonpayg(offer=None, addon_offer=None):
    """Whether the device picker should list auto-generated Non-PAYG Device.

    Auto-generated NPG has no product subtype, so it is hidden when the offer
    (or addon offer) is restricted to a specific subtype. Those devices must
    be uploaded by CSV.

    Contract offers restricted only to NPG (no subtype) still show the option
    (SB-969). Addon offers with any product_type restriction keep hiding it
    (SB-908). When there is no offer, the NPGDeviceEnabled setting applies.
    """
    if not SettingsService.get_setting('NPGDeviceEnabled'):
        return False

    if addon_offer is not None:
        if addon_offer.product_type or addon_offer.product_sub_type:
            return False
        return True

    if offer is None:
        return True

    if offer.device_type and offer.device_type != NON_PAYG_TYPE:
        return False

    if offer.product_sub_type:
        return False

    return True


def should_force_auto_generated_nonpayg(offer):
    """Auto-select Non-PAYG Device only for NPG offers with no subtype."""
    return bool(offer and offer.device_type == NON_PAYG_TYPE and not offer.product_sub_type)
