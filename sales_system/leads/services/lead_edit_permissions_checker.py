from shared.logger.loggers import Error


class EditLeadPermissionChecker:

    @classmethod
    def check_permissions(cls, lead, user):
        if lead.awaiting_delivery and lead.already_paid != 0 and (not user.can_access('EditOfferAwaitingDeliveryLeads', person=lead.person) or lead.offer_editing_locked):
            raise Error('EDIT_LEAD_AWAITING_DELIVERY_NOT_ALLOWED')
        if lead.already_paid and not lead.awaiting_delivery and (not user.can_access('EditOfferPartiallyPaidLeads', person=lead.person) or lead.offer_editing_locked):
            raise Error('EDIT_LEAD_PARTIALLY_PAID_NOT_ALLOWED')