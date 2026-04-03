from payg_loan_system.payments.models.wallet import PaymentWallet
from shared.services.base_getter_service import BaseGetterService


class WalletGetterService(BaseGetterService):

    OBJ_NAME = 'Wallet'

    @classmethod
    def get_filtered_objects(cls, current_user=None, **kwargs):
        return PaymentWallet.select()

