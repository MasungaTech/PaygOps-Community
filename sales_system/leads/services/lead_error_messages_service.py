
from messages_system.services.message_service import MessageService
from shared.services.translation_service import TranslationService


class Error(Exception):
    pass


class LeadErrorMessagesService:

    @classmethod
    def get_human_readable_error(cls, error, user):
        # Generic insufficient permission handler (with permission name), using message templates
        if 'INSUFFICIENT_PERMISSION' in str(error):
            return MessageService.get_message({'status': str(error), 'permission': getattr(error, 'data', {}).get('permission')})
        if 'CANNOT_EDIT_INSTALLED_LEAD' in str(error):
            return 'Installed Leads cannot be edited. '
        if 'CANNOT_EDIT_CANCELLED_LEAD' in str(error):
            return 'Cancelled Leads cannot be edited. '
        if 'INVALID_PAYMENT_REFERENCE' in str(error):
            return 'Invalid payment reference. '
        if 'LEAD_DOES_NOT_EXIST_OR_NO_PERMISSIONS' in str(error):
            return 'The Lead does not exists or you do not have the permission to edit it. '
        if 'INVALID_VILLAGE_ID' in str(error):
            return 'Invalid L0 entity ID. '
        if 'INVALID_OFFER_ID' in str(error):
            return 'Invalid Offer ID. '
        if 'LEAD_HAS_LOAN_ADDONS' in str(error):
            return 'This lead has loan addons and the new offer do not accept loan addons. Please remove those addons first. '
        if 'LEAD_OFFER_NOR_VALID_WITH_DURATION_ADDONS' in str(error):
            return 'This lead has duration loan addons and the new offer configuration will have 0 reference price. Please remove those addons first. '
        if 'VILLAGE_REQUIRED' in str(error):
            return 'It is required to provide a village to add a lead. '
        if 'LEAD_STATUS_REQUIRED' in str(error):
            return 'It is required to provide a status to add a lead. '
        if 'FORBIDDEN_STATUS_FOR_NEW_LEAD' in str(error):
            return 'This status is forbidden for new leads. '
        if 'LEAD_GENERATOR_REQUIRED' in str(error):
            return 'It is required to provide a lead generator to add a lead. '
        if 'NAME_REQUIRED' in str(error):
            return 'It is required to provide a name to add a lead. '
        if 'SURNAME_REQUIRED' in str(error):
            return 'It is required to provide a surname to add a lead. '
        if 'NAME_AND_PHONE_NUMBER_ALREADY_EXISTS' in str(error):
            return 'The name and phone number already match an existing lead, make sure it is not a duplicate. '
        if 'CANNOT_CHANGE_OFFER_ON_PAID_LEADS' in str(error):
            return 'The offer cannot be changed on leads that have already paid. ' \
                   'Refund the downpayment before changing offer. '
        if 'EDIT_LEAD_AWAITING_DELIVERY_NOT_ALLOWED' in str(error):
            return 'You do not have the permission to edit this lead\'s offer when the downpayment is fully paid.'
        if 'EDIT_LEAD_PARTIALLY_PAID_NOT_ALLOWED' in str(error):
            return 'You do not have the permission to edit this lead\'s offer when the downpayment is partially paid.'
        if 'THIS_STATUS_CANNOT_BE_SET_MANUALLY' in str(error):
            return 'The status you selected cannot be set directly for a Lead. Make sure you follow the process. '
        if 'INSUFFICIENT_PERMISSION_TO_APPROVE_LEADS' in str(error):
            return 'You do not have sufficient permission to approve leads. '
        if 'LEAD_NOT_AWAITING_PAYMENT' in str(error):
            return 'The Lead is not awaiting payment. Make sure it is awaiting payment before associating. '
        if 'LEAD_HAS_NO_OFFER' in str(error):
            return 'The lead needs to have an offer before approval. '
        if 'PAYMENT_ALREADY_USED' in str(error):
            return 'The payment selected was already used. '
        if 'LEAD_INSUFFICIENT_BALANCE' in str(error):
            deposit_value = error.args[1].get('deposit_value') if len(error.args) > 0 else None
            if deposit_value:
                return TranslationService.ftext('The account does not have sufficient balance to pay downpayment of {deposit_value}. ', deposit_value, user=user)
            return 'The account does not have sufficient balance to pay downpayment. '
        if 'PAYMENT_ACCOUNT_ALREADY_OWNED_BY_CLIENT' in str(error):
            client_id = error.args[1].get('client_id') if len(error.args) > 0 else ''

            return TranslationService.ftext('The payment wallet is already owned by the client with ID {}', client_id, user=user)
        if 'PAYMENT_ACCOUNT_ALREADY_OWNED_BY_LEAD' in str(error):
            lead_id = error.args[1].get('lead_id') if len(error.args) > 0 else ''
            message = 'The payment wallet is already owned by the lead with ID {lead_id}. '
            message += 'You must refund downpayment for that lead before using it here. '
            message += '</span> | <br><a onclick="refundLeadDeposit(\'{lead_id}\');" style="cursor: pointer;">' \
                '<strong>REFUND DOWNPAYMENT</strong></a> '
            message = TranslationService.ftext(message, lead_id=lead_id, user=user)
            return message
        if 'CAN_ONLY_REFUND_PAID_LEADS' in str(error):
            return 'You can only refund the downpayment for leads that have paid it already. '
        if 'MULTIPLE_PAYMENT_FOUND' in str(error):
            return 'Multiple payments found with that reference. Use the payment list to find and reconcile the payment you want.'
        if 'DEPOSIT_CANNOT_BE_REFUNDED' in str(error):
            return 'The deposit cannot be refunded since the offer is not locked'
        if 'PAYMENT_WAS_DELETED' in str(error):
            return 'Could not refund the downpayment because the payment(s) used to pay it have been deleted or reverted. '
        if 'INVALID_COMMISSION_VALUE' in str(error):
            return 'The commission value is invalid, make sure to type only number without commas. '
        if 'LEAD_ALREADY_PAID_CANNOT_CHANGE_STATUS' in str(error):
            return 'The lead has already paid, refund the payment before changing the status. '
        if 'LEAD_IS_NOT_COMPLETE' in str(error):
            return 'The Lead is not complete, please make sure all forms are filled and an active offer is selected. '
        if 'LEAD_IS_COMPLETE' in str(error):
            return 'The Lead is already complete and cannot be Awainting Information. '
        if 'LEAD_NOT_APPROVED' in str(error):
            return f'The Lead needs to be approved. '
        if 'STATUS_NOT_ALLOWED' in str(error):
            return TranslationService.ftext('The new status "{}" is not allowed for leads in status "{}". ', error.args[1], error.args[2], user=user)
        if 'PHONE_NUMBER_ALREADY_OWNED' in str(error):
            return 'The phone number is already owned by someone else. Edit on the platform to solve the issue. '
        if 'OFFER_CANNOT_BE_APPROVED' in str(error):
            return 'A lead with this offer cannot be approved because this offer is no longer active. '
        if 'PHONE_NUMBER_TOO_SHORT' in str(error):
            return TranslationService.ftext('The phone number "{}" is too short. Make sure there are no less than {} digits. ', error.data.get('phone_number'), error.data.get('min_length'), user=user)
        if 'PHONE_NUMBER_TOO_LONG' in str(error):
            return TranslationService.ftext('The phone number "{}" is too long. Make sure there are no more than {} digits. ', error.data.get('phone_number'), error.data.get('max_length'), user=user)
        return None
