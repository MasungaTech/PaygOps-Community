from pony.orm.core import select, count
from core_system.client.models import Client
from payg_loan_system.payments.models.wallet import PaymentWallet, PaymentWalletType
from pony import orm
from worker_app.worker_app import worker_app


@worker_app.task
@orm.db_session(sql_debug=False)
def migrate_cash_wallets():
    print('Migrating clients with multiple cash accounts')
    page_items = 1000
    clients_all = get_clients_to_migrate()
    count = clients_all.count()
    print(str(count)+' clients to migrate')
    while count != 0:
        clients = clients_all.page(1, page_items)
        for client in clients:
            migrate_payments_and_delete_wallets(client)
        orm.commit()
        client_all = get_clients_to_migrate()
        count = client_all.count()
        print(str(count) + ' left to migrate')

def migrate_payments_and_delete_wallets(client):
    cash_wallets = [wallet for wallet in client.payment_wallets if wallet.Type == PaymentWalletType.cash]
    if len(cash_wallets) <= 1:
        return
    first_wallet = cash_wallets[0]
    for i in range(1, len(cash_wallets)):
        first_wallet.Payments.add(cash_wallets[i].Payments)
        first_wallet.payment_debits.add(cash_wallets[i].payment_debits)
        client.payment_wallets.remove(cash_wallets[i])
    
def get_clients_to_migrate():
    return select(c for c in Client if count(w for w in c.payment_wallets if w.Type == PaymentWalletType.cash) > 1)