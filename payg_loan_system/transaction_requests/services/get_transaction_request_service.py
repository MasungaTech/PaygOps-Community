from werkzeug.exceptions import NotFound
from payg_loan_system.transaction_requests.models import TransactionRequest
from sales_system.leads.models.lead import Lead
from shared.api_helpers.server_helpers.jwt_and_schema_verification import check_permissions_for_user
from shared.logger.loggers import LogAPI
from shared.services.base_getter_service import BaseGetterService

log_api = LogAPI()


class GetTransactionRequestService(BaseGetterService):

    @classmethod
    def get_filtered_objects(cls, current_user=None, acting_user=None, offline=None, success='NOT_SET', **kwargs):
        transactions = TransactionRequest.select()
        if acting_user is not None:
            transactions = transactions.filter(lambda t: t.user == acting_user)
        if offline is not None:
            transactions = transactions.filter(lambda t: t.offline == offline)
        if success != 'NOT_SET': # this is to be able to filter by success == None
            transactions = transactions.filter(lambda t: t.success == success)
        return transactions
    
    @classmethod
    def get_list_for_mobile(cls, current_user, cached_ids, **kwargs):
        return cls.get_list(current_user, acting_user=current_user, offline=True, success=None)

    @classmethod
    def get_transaction_request_answer(cls, user, uuid, human_readable):
        this_transaction = cls.get_transaction(uuid)
        if not this_transaction:
            raise NotFound('Transaction not found')
        check_permissions_for_user(user, ['ViewActions'], person=this_transaction._get_affected_person())
        return this_transaction.get_serialized_object(human_answer=human_readable)

    @classmethod
    def get_transaction(cls, uuid):
        return TransactionRequest.get(uuid=uuid)
    
    @classmethod
    def get_transaction_by_id(cls, id):
        return TransactionRequest.get(id=id)
