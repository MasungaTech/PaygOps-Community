from shared.helpers.db_helpers import TypeClassBase


class StatusCategory(TypeClassBase):
    to_be_convinced = 'To be convinced'
    awaiting_information = 'Awaiting Information'
    awaiting_decision = 'Awaiting Decision'
    awaiting_payment = 'Awaiting Payment'
    awaiting_delivery = 'Awaiting Delivery'
    installed = 'Installed'
    inactive = 'Inactive'
    discarded = 'Discarded'
    cancelled = 'Cancelled'

# WARNING: Even though inactive or discarded statuses can be chosen as part of the decision process
# they shouldn't have the "decision" attribute which is really meant for approval to avoid inconsistencies
AWAITING_INFO_OR_BEFORE_CATEGORIES = [
    StatusCategory.awaiting_information,
    StatusCategory.to_be_convinced, 
    StatusCategory.inactive,
    StatusCategory.discarded
]

DECISION_MADE_CATEGORIES = [
    StatusCategory.awaiting_payment, 
    StatusCategory.awaiting_delivery,
    StatusCategory.installed
]

NO_DECISION_CATEGORIES = AWAITING_INFO_OR_BEFORE_CATEGORIES + [StatusCategory.awaiting_decision]


BILLING_INACTIVE_CATEGORIES = [
    StatusCategory.installed, 
    StatusCategory.inactive, 
    StatusCategory.discarded, 
    StatusCategory.cancelled
]