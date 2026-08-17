from datetime import datetime
from shared.services.base_service import BaseService
from shared.model.billing import Bill
from shared.logger.loggers import Error


class BillEditService(BaseService):

    @classmethod
    def _edit_from_data_and_user(cls, obj, data, user, **kwargs):
        bill = obj

        if id in data:
            try:
                override_bill = Bill.get(id=data['id'])

            except Exception as e:
                raise Error(f'Error retrieving bill: {str(e)}') from e
            
            if not override_bill:
                raise Error(f'Bill with id {data["id"]} not found.')
            bill = override_bill
            
        if not bill:
            raise Error('Bill not found. Please provide a valid bill id in the request data or use a billing URL that points to an existing bill.')
        
        try:
            if 'extra_billing_info' in data:
                bill.extra_billing_info = data['extra_billing_info']
        except Exception as e:
            raise Error(f'Error updating bill extra_billing_info: {str(e)}') from e
        
        return bill

