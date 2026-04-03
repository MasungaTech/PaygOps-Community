from tempfile import TemporaryFile
from pony import orm
from decimal import Decimal
from payg_loan_system.contracts.models.repayment_model import ContractRepayment
from payg_loan_system.contracts.models.repayment_discount_types import ContractRepaymentDiscountTypes
from worker_app.worker_app import worker_app
import math


@worker_app.task
def populate_credit_value():
    # we do 3 passes to ensure everything is covered, even though with that strategy everything should
    print('Populating credit_value for repayments - Pass 1')
    try:
        populate_credit_pass()
    except Exception as e:
        pass
    print('Populating credit_value for repayments - Pass 2')
    try:
        populate_credit_pass()
    except Exception as e:
        pass
    print('Populating credit_value for repayments - Pass 3')
    try:
        populate_credit_pass()
    except Exception as e:
        pass


def populate_credit_pass():
    page_size = 1000
    with orm.db_session:
        all_repayments = get_all()
        count = all_repayments.count()
    number_of_pages = math.ceil(count / page_size)
    for page_n in range(1, number_of_pages + 1):
        try:
            with orm.db_session:
                process_page(all_repayments, page_n, number_of_pages, page_size)
        except Exception as e:
            with orm.db_session:
                process_page(all_repayments, page_n, number_of_pages, page_size)


def process_page(all_repayments, page_n, number_of_pages, page_size):
    # We do the pages in reverse because the list size reduces with the passes
    print(f'Page {page_n} of {number_of_pages} - {(number_of_pages+1)-page_n}')
    repayments = all_repayments.page((number_of_pages+1)-page_n, page_size)
    for repayment in repayments:
        credit_value = get_credit_value(repayment)
        if credit_value:
            repayment.credit_value = Decimal(str(round(credit_value, 2)))
            repayment.amount_late = Decimal(str(round(repayment.amount_late or 0, 2))) #that's needed for some dbs with corrupted data
    orm.commit()

        

def get_all():
    return ContractRepayment.select(lambda r: (r.credit_value is None or r.credit_value == 0) and r.discount_type in [
        ContractRepaymentDiscountTypes.manual_delay,
        ContractRepaymentDiscountTypes.offer_change_delay,
        ContractRepaymentDiscountTypes.prepayment,
        '',
        ContractRepaymentDiscountTypes.downpayment
    ])


def get_credit_value(repayment):
    if repayment.discount_type in [ContractRepaymentDiscountTypes.manual_delay, ContractRepaymentDiscountTypes.offer_change_delay]:
        return repayment.delay_given_in_hours
    if repayment.discount_type in [ContractRepaymentDiscountTypes.prepayment, '']:
        return repayment.contract.get_units_from_amount(repayment.amount_paid, time=repayment.time, allow_below_minimum=True)
    if repayment.discount_type == ContractRepaymentDiscountTypes.manual_discount:
        return repayment.contract.get_units_from_amount(repayment.amount_discounted, allow_below_minimum=True, time=repayment.time)
    if repayment.discount_type == ContractRepaymentDiscountTypes.downpayment:
        return repayment.contract.offer_at(repayment.time).free_credit_at_start