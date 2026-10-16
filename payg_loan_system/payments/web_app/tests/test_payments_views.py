import pytest

from pony.orm import db_session
from tests.base_test import BaseViewTest


class TestListPayments(BaseViewTest):
    url = 'payment.list_payment'
    template = 'list_payment.html'


class TestViewPaymentWallet(BaseViewTest):
    url = 'payment.account'
    template = 'view_payment_wallet.html'
    params = dict(account_id=1)


class TestEditPaymentWallet(BaseViewTest):
    url = 'payment.edit_account'
    template = 'edit_payment_wallet.html'
    params = dict(account_id=1)

class TestMpesaFixer(BaseViewTest):
    url = 'payment.add_manual_payment'
    template = 'manual_payments_form.html'
    allowed_methods = ['GET', 'POST']

    form = dict(payment_ref='ABCDEFGHIJ',
                amount='12345',
                payment_wallet_name='TESTING',
                wallet_operator='MTN',)

    @db_session
    def test_unregistered_mpesa_reference_name(self, super_admin_app):

        res = self.post(super_admin_app, self.form)

        assert res.template_is('manual_payments_form.html')
        assert b'Payment added successfully!' in res.data

    @db_session
    def test_duplicate_mpesa_reference(self, super_admin_app):
        res = self.post(super_admin_app, self.form)

        assert res.template_is('manual_payments_form.html')
        assert b'A payment with that reference already exists' in res.data

    @db_session
    def test_mpesa_reference_name_list(self, super_admin_app):
        self.form['payment_wallet_name_list'] = 'TESTING'
        res = self.post(super_admin_app, self.form)

        assert res.template_is('manual_payments_form.html')
        assert b'A payment with that reference already exists' in res.data
