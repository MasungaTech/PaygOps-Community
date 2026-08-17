from decimal import Decimal
from mock import patch
from payg_loan_system.offers.tests.factories import TimeOfferFactory
from sales_system.leads.services.lead_status_change_service import LeadStatusChangeService
from sales_system.leads.tests.factories import LeadFactory


class TestLeadStatusChangeServiceApproveLead:

    def _lead(self, registration_fee):
        offer = TimeOfferFactory.stub(registration_fee=Decimal(registration_fee))
        lead = LeadFactory.stub(offer=offer, decision=False, decisionMaker=None)
        lead.deposit_paid = False
        lead.already_paid = 0
        lead.left_to_pay = Decimal(registration_fee)
        return lead

    @patch('sales_system.leads.services.lead_status_change_service.MessageService.send_answer_to_person')
    def test_approve_lead_with_downpayment_sends_awaiting_payment_sms(self, send_sms):
        lead = self._lead(registration_fee=100)
        LeadStatusChangeService.approve_lead(lead, set_status=False)

        send_sms.assert_called_once()
        status, person = send_sms.call_args[0]
        assert status['status'] == 'LEAD_APPROVED_AND_AWAITING_PAYMENT'
        assert float(status['deposit_value']) == 100
        assert status['name'] == lead.person.name
        assert status['surname'] == lead.person.surname
        assert status['offer_name'] == lead.offer.name
        assert status['free_time'] == lead.offer.free_credit_at_start
        assert status['contract_reference'] == lead.future_contract_reference
        assert person == lead.person

    @patch('sales_system.leads.services.lead_status_change_service.MessageService.send_answer_to_person')
    def test_approve_lead_without_downpayment_sends_no_downpayment_sms(self, send_sms):
        lead = self._lead(registration_fee=0)
        LeadStatusChangeService.approve_lead(lead, set_status=False)

        send_sms.assert_called_once()
        status, person = send_sms.call_args[0]
        assert status['status'] == 'LEAD_APPROVED_NO_DOWNPAYMENT'
        assert status['name'] == lead.person.name
        assert status['surname'] == lead.person.surname
        assert status['offer_name'] == lead.offer.name
        assert status['free_time'] == lead.offer.free_credit_at_start
        assert status['contract_reference'] == lead.future_contract_reference
        assert person == lead.person

    @patch('sales_system.leads.services.lead_status_change_service.MessageService.send_answer_to_person')
    def test_approve_lead_send_sms_false_skips_sms_with_downpayment(self, send_sms):
        lead = self._lead(registration_fee=100)
        LeadStatusChangeService.approve_lead(lead, set_status=False, send_sms=False)
        send_sms.assert_not_called()

    @patch('sales_system.leads.services.lead_status_change_service.MessageService.send_answer_to_person')
    def test_approve_lead_send_sms_false_skips_sms_without_downpayment(self, send_sms):
        lead = self._lead(registration_fee=0)
        LeadStatusChangeService.approve_lead(lead, set_status=False, send_sms=False)
        send_sms.assert_not_called()
