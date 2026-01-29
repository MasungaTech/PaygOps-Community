from datetime import datetime
from shared.services.base_service import BaseService
from shared.model.billing import Bill
from shared.logger.loggers import Error


class BillEditService(BaseService):

    @classmethod
    def _edit_from_data_and_user(cls, obj, data, user, **kwargs):
        bill = None
        
        try:
            # Retrieve bill from data if id is provided
            if 'id' in data:
                bill = Bill.get(id=data['id'])
                if not bill:
                    raise Error(f'Bill with id {data["id"]} not found.')
            else:
                # Use current date (normalized to first of month) to get the bill
                current_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                bill = Bill.get(date=current_date)
                if not bill:
                    raise Error(f'Bill for date {current_date.strftime("%Y-%m-%d")} not found. Please ensure a bill exists for the current month.')
        except Exception as e:
            raise Error(f'Error retrieving bill: {str(e)}') from e
        

        if not bill:
            bill = obj
            if not bill:
                raise Error('Bill not found. Please provide bill id in the request data, or ensure a bill exists for the current month.')
        
        try:
            if 'extra_billing_info' in data:
                bill.extra_billing_info = data['extra_billing_info']
        except Exception as e:
            raise Error(f'Error updating bill extra_billing_info: {str(e)}') from e
        
        return bill

