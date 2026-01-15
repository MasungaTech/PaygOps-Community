from datetime import datetime
from core_system.users.models.user_model import User
from payg_loan_system.offers.models import OfferType
from sales_system.leads.models.lead_status import LeadStatus
from sales_system.leads.models.status_change_history import StatusChangesHistory
from sales_system.leads.models.status_category import BILLING_INACTIVE_CATEGORIES, StatusCategory, AWAITING_INFO_OR_BEFORE_CATEGORIES, DECISION_MADE_CATEGORIES, NO_DECISION_CATEGORIES
from messages_system.services.message_service import MessageService
from shared.api_helpers.hook_helpers.process_hook import add_hook_after_commit
from shared.helpers.numbers import round_if_exists
from shared.logger.loggers import Error, LogAPI
from shared.services.settings_service import SettingsService
from core_system.core_entities import db
from pony.orm import desc

log_api = LogAPI()


class LeadStatusChangeService:

    @classmethod
    def update(cls, lead, autoreconcile_from_client=True):
        # We fix incoherence needed to be fixed before auto-update
        cls.fix_status_issues(lead, pre=True, post=False)
        INCOMPLETE_STATUSES = [StatusCategory.to_be_convinced, StatusCategory.awaiting_information, StatusCategory.installed, StatusCategory.discarded, StatusCategory.inactive, StatusCategory.cancelled]
        # We downgrade the status to awaiting information if it's not complete anymore with the new offers (e.g. more forms required)
        if lead.status.category not in INCOMPLETE_STATUSES and not cls.lead_is_complete(lead):
            cls._set_first_of_category(lead, StatusCategory.awaiting_information, status_comment='Automatically moved to awaiting information due to missing information')
        # if the lead was awaiting information and is now complete, we set it to awaiting decision
        if lead.status.category == StatusCategory.awaiting_information and cls.lead_is_complete(lead):
            cls._set_first_of_category(lead, StatusCategory.awaiting_decision,
                                       status_comment='Automatically updated to Awaiting Decision')
        # if the lead was awaiting decision but can be auto-approved, we set it to approved
        if (lead.status.category == StatusCategory.awaiting_decision and lead.offer
            and lead.offer.no_approval_required and not lead.addons.filter(lambda a: a.offer_version.offer.need_approval).count()):
            cls.approve_lead(lead, status_comment='Automatically Approved')
        # if it was awaiting payment but is now paid, we set it to awaiting delivery
        if lead.status.category == StatusCategory.awaiting_payment and lead.deposit_paid and lead.offer_editing_locked:
            cls._set_first_of_category(lead, StatusCategory.awaiting_delivery)
        # if it was awaiting delivery but payment has been reverted, we it back to awaiting payment
        if lead.status.category == StatusCategory.awaiting_delivery and not lead.deposit_paid:
            cls._set_first_of_category(lead, StatusCategory.awaiting_payment)
        # if it was awaiting delivery and now has a contract, we set it as installed
        if lead.status.category == StatusCategory.awaiting_delivery and lead.installed:
            cls._set_first_of_category(lead, StatusCategory.installed)
        
        if SettingsService.get_setting('AutoRegisterLeadWithDownpaymentAndDevice') and lead.status.category == StatusCategory.awaiting_delivery and lead.allocated_device and not lead.based_on_lead:
            acting_user = User.get(username="system@solarisoffgrid.com")
            from payg_loan_system.actions.registration import register_lead
            answer = register_lead(acting_user=acting_user, this_lead=lead, this_device=lead.allocated_device)
            # No need to send the answer as the welcome message is already sent

        if autoreconcile_from_client and SettingsService.get_setting('AutoReconcilePendingPayments') and lead.status.category == StatusCategory.awaiting_payment and lead.person.pending_reconciled_payments_filtered.count():
            from payg_loan_system.payments.services.reconciliation_service import ReconciliationService
            ReconciliationService.reconcile_pending_payments_to_lead(lead)

        # We check and fix any incoherence that might remain
        cls.fix_status_issues(lead, pre=False, post=True)
        return lead

    @classmethod
    def fix_status_issues(cls, lead, pre=True, post=True):
        # Checks to be done before the auto-changes are done
        if pre:
            # If lead is in an approved status but not approved we add the decision
            if lead.status.category in DECISION_MADE_CATEGORIES and not lead.decision:
                lead.decision = True
                log_api.Warning(f'Lead [{lead.id}] should have had a decision but did not')
            # If lead is in an unapproved status but has decision, we remove the decision
            if lead.decision and lead.status.category in NO_DECISION_CATEGORIES:
                cls.remove_lead_approval(lead)
                log_api.Warning(f'Lead [{lead.id}] should not have had a decision but did')

        # Checks to be done after the auto-changes are done
        if post:
            if lead.inactive and lead.status.category != StatusCategory.inactive:
                cls._set_first_of_category(lead, StatusCategory.inactive)
                log_api.Warning(f'Lead [{lead.id}] was inactive but with incorrect status')
            if lead.discarded and lead.status.category != StatusCategory.discarded:
                cls._set_first_of_category(lead, StatusCategory.discarded)
                log_api.Warning(f'Lead [{lead.id}] was discarded but with incorrect status')
            if lead.to_be_convinced and lead.status.category != StatusCategory.to_be_convinced:
                cls._set_first_of_category(lead, StatusCategory.awaiting_delivery)
                log_api.Warning(f'Lead [{lead.id}] was to_be_convinced but with incorrect status')
            if lead.awaiting_information and lead.status.category != StatusCategory.awaiting_information:
                cls._set_first_of_category(lead, StatusCategory.awaiting_information)
                log_api.Warning(f'Lead [{lead.id}] was awaiting_information but with incorrect status')
            if lead.awaiting_decision and lead.status.category != StatusCategory.awaiting_decision:
                cls._set_first_of_category(lead, StatusCategory.awaiting_decision)
                log_api.Warning(f'Lead [{lead.id}] was awaiting_decision but with incorrect status')
            if lead.awaiting_payment and lead.status.category != StatusCategory.awaiting_payment:
                cls._set_first_of_category(lead, StatusCategory.awaiting_payment)
                log_api.Warning(f'Lead [{lead.id}] was awaiting_payment but with incorrect status')
            if lead.awaiting_delivery and lead.status.category != StatusCategory.awaiting_delivery:
                cls._set_first_of_category(lead, StatusCategory.awaiting_delivery)
                log_api.Warning(f'Lead [{lead.id}] was awaiting_delivery but with incorrect status')
            if lead.installed and lead.status.category != StatusCategory.installed:
                cls._set_first_of_category(lead, StatusCategory.installed)
                log_api.Warning(f'Lead [{lead.id}] was installed but with incorrect status')
            if lead.cancelled and lead.status.category != StatusCategory.cancelled:
                cls._set_first_of_category(lead, StatusCategory.cancelled)
                log_api.Warning(f'Lead [{lead.id}] was cancelled but with incorrect status')
            if not lead.installed and lead.status.category == StatusCategory.installed:
                status_ids = [sch.status_id.id for sch in lead.status_changes_history.order_by(lambda sch: desc(sch.date))]
                for sid in status_ids:
                    status = LeadStatus.get(id=sid)
                    if status.category != StatusCategory.installed: break
                else:
                    status = None
                if status:
                    cls.set_status(lead, status)
                    log_api.Warning(f'Lead [{lead.id}] was in intalled status but with no contract')

            if not lead.to_be_convinced and not lead.awaiting_information and not lead.awaiting_decision \
            and not lead.awaiting_payment and not lead.awaiting_delivery and not lead.installed \
            and not lead.inactive and not lead.discarded and lead.offer_editing_locked:
                log_api.Warning(f'Lead [{lead.id}] is in a status black hole')

    @classmethod
    def offer_change_update(cls, lead, user):
        # We remove the decision after offer change if needed
        if lead.status.category in DECISION_MADE_CATEGORIES or lead.decision:
            cls.remove_lead_approval(lead, user, status_comment='Automatically Unapproved after offer change')
        # We perform a regular update to also change other status as needed
        cls.update(lead)

    @classmethod
    def get_allowed_statuses_from_category(cls, status_category):
        # We remove awaiting info and only add it if the lead is not complete as it would automatically get changed otherwise
        info_or_before = AWAITING_INFO_OR_BEFORE_CATEGORIES.copy()
        if status_category == StatusCategory.cancelled:
            return LeadStatus.select(lambda s: s.category == StatusCategory.cancelled)
        if status_category == StatusCategory.installed:
            return LeadStatus.select(lambda s: s.category == StatusCategory.installed)
        if status_category == StatusCategory.awaiting_delivery:
            return LeadStatus.select(lambda s: s.category in [StatusCategory.awaiting_delivery,
                                                                StatusCategory.awaiting_decision, StatusCategory.installed] + info_or_before)
        if status_category == StatusCategory.awaiting_payment:
            return LeadStatus.select(lambda s: s.category in [StatusCategory.awaiting_payment, StatusCategory.awaiting_decision] + info_or_before)
        if status_category == StatusCategory.awaiting_decision:
            return LeadStatus.select(lambda s: s.category in [StatusCategory.awaiting_decision] + info_or_before)
        if status_category == 'new': # This is for new leads in the UI
            return LeadStatus.select(lambda s: s.category == StatusCategory.to_be_convinced or s.category == StatusCategory.awaiting_information)
        info_or_before.append(StatusCategory.awaiting_information)
        return LeadStatus.select(lambda s: s.category in info_or_before)

    @classmethod
    def get_allowed_statuses_from_lead(cls, lead, user, manual=False):

        # System restrictions
        statuses = cls.get_allowed_statuses_from_category(lead.status.category)

        # User-defined restrictions
        if not user.can_access('MoveToRestrictedStatusLeads', person=lead.person):
            restricted_statuses = SettingsService.get_setting('statusTransitionRestrictions').get(str(lead.status.id), [])
            statuses = statuses.filter(lambda s: s.id not in restricted_statuses)
        
        # Lead real situation restrictions
        if lead.status.category not in [StatusCategory.to_be_convinced, StatusCategory.discarded, StatusCategory.inactive] and cls.lead_is_complete(lead):
            statuses = statuses.filter(lambda s: s.category != StatusCategory.awaiting_information)
        if lead.awaiting_delivery and lead.downpayment != 0:
            statuses = statuses.filter(lambda s: s.category == StatusCategory.awaiting_delivery or s.category == StatusCategory.installed)
        if manual:
            statuses = statuses.filter(lambda s: s.category != StatusCategory.installed)
        return statuses

    @classmethod
    def _set_first_of_category(cls, lead, category, status_comment='', user=None):
        cls.set_status(lead, LeadStatus.get_first(category), status_comment, user)

    @classmethod
    def set_status(cls, lead, status, status_comment='', user=None):
        if lead.installed and lead.status.category == StatusCategory.installed and status.category not in [StatusCategory.installed, StatusCategory.cancelled]:
            raise Error('CANNOT_EDIT_INSTALLED_LEAD')
        if lead.cancelled and status.category != StatusCategory.cancelled:
            raise Error('CANNOT_EDIT_CANCELLED_LEAD')
        paids = [StatusCategory.installed, StatusCategory.awaiting_delivery]
        if lead.deposit_paid and lead.offer_editing_locked and lead.already_paid > 0 and lead.status in paids and status.category not in paids:
            raise Error('LEAD_ALREADY_PAID_CANNOT_CHANGE_STATUS', lead.status.category, status.category)
        if lead.offer and not lead.offer.in_use and status.category == StatusCategory.awaiting_payment and lead.status.category != StatusCategory.awaiting_delivery:
            raise Error('OFFER_CANNOT_BE_APPROVED')
        if cls.pre_approval(lead) and not lead.decision and status.category in [StatusCategory.awaiting_payment,
                                                                                StatusCategory.awaiting_delivery,
                                                                                StatusCategory.installed]:
            raise Error('LEAD_NOT_APPROVED')
        if cls.pre_approval(lead) and (not LeadStatusChangeService.lead_is_complete(lead) and
                status.category not in [StatusCategory.to_be_convinced, StatusCategory.awaiting_information,
                                        StatusCategory.discarded, StatusCategory.inactive]):
            raise Error('LEAD_IS_NOT_COMPLETE')
        if status.category == StatusCategory.awaiting_information and LeadStatusChangeService.lead_is_complete(lead) and \
                lead.status.category in [StatusCategory.awaiting_decision, StatusCategory.awaiting_payment]:
            raise Error('LEAD_IS_COMPLETED')
        # if cancelling the approval
        if lead.decision and status.category in NO_DECISION_CATEGORIES:
            cls.remove_lead_approval(lead, set_status=False)
        # In case of automatic approval on mobile and then switch to another status
        # this is not set. In that case we don't want to send the SMS.
        if not lead.decision and status.category in DECISION_MADE_CATEGORIES:
            cls.approve_lead(lead, set_status=False, send_sms=False)
        if lead.status != status:
            lead.statusUpdate = datetime.now()
        lead.status = status
        lead.status_comment = status_comment
        cls.create_status_change_from_lead(lead, user)
        

    @staticmethod
    def pre_approval(lead):
        return not lead.installed and not lead.cancelled and not lead.awaiting_delivery and not lead.awaiting_payment

    @classmethod
    def remove_lead_approval(cls, this_lead, user=None, status_comment='', set_status=True):
        this_lead.decision = False
        this_lead.decisionMaker = None
        this_lead.decisionTime = None
        if set_status and this_lead.status.category in DECISION_MADE_CATEGORIES:
            cls._set_first_of_category(this_lead, StatusCategory.awaiting_decision, status_comment=status_comment)
        add_hook_after_commit(db, 'lead_edited', this_lead.get_serialized_object())

    @classmethod
    def approve_lead(cls, lead, status_comment='', user=None, check_permissions=True, send_sms=True, set_status=True):
        if user and check_permissions and not user.can_access('ApproveLeads', person=lead.person):
            raise Error('INSUFFICIENT_PERMISSION_TO_APPROVE_LEADS')
        lead.decision = True
        lead.decisionMaker = user
        lead.decisionTime = datetime.now()
        if set_status:
            cls._set_first_of_category(lead, StatusCategory.awaiting_payment,
                                    status_comment=status_comment, user=user)
        if send_sms and lead.downpayment > 0 and not lead.deposit_paid:
            status = {
                'status': 'ADDITIONAL_DOWN_PAYMENT_REQUIRED',
                'still_to_pay': round_if_exists(lead.left_to_pay),
                'amount': round_if_exists(lead.downpayment),
                'already_paid': lead.already_paid,
            } if lead.already_paid else {
                'status': 'LEAD_APPROVED_AND_AWAITING_PAYMENT',
                'still_to_pay': round_if_exists(lead.left_to_pay),
                'deposit_value': round_if_exists(lead.downpayment),
                'name': lead.person.name,
                'surname': lead.person.surname,
                'offer_name': lead.offer.name,
                'free_time': lead.offer.free_credit_at_start,
                'contract_reference': lead.future_contract_reference
            }
            MessageService.send_answer_to_person(status, lead.person)

    @classmethod
    def lead_is_complete(cls, lead):
        return lead.offer \
            and lead.offer.in_use \
            and lead.info_completed \
            and ((lead.reference_price != 0 
                  or (lead.offer.type == OfferType.lump_sum and lead.downpayment != 0))
                or (lead.offer.base_price_amount_can_be_negative and lead.reference_price <= 0))

    @classmethod
    def create_status_change_from_lead(cls, this_lead, user=None):
        this_status_change = StatusChangesHistory(
            lead=this_lead,
            date=datetime.now(),
            status=this_lead.status.name,
            status_id=this_lead.status.id,
            next_contact=this_lead.nextContact,
            status_comment=this_lead.status_comment,
        )
        this_status_change.reasons_for_not_buying.add(this_lead.reasons_for_not_buying)
        current_time = datetime.now()
        this_lead.modifiedDate = current_time
        
        # Update timestamps based on current status (this is called when status changes)
        if this_lead.status.category in BILLING_INACTIVE_CATEGORIES:
            # Lead is in an inactive status - set last_time_inactive
            this_lead.last_time_inactive = current_time
        else:
            # Lead is in an active status - update last_time_active
            this_lead.last_time_active = current_time

    @classmethod
    def cancel_lead(cls, lead, user):
        cls._set_first_of_category(lead, StatusCategory.cancelled, status_comment=f'Lead cancelled by {user.full_name}', user=user)
        lead.status = LeadStatus.get_first(StatusCategory.cancelled)
