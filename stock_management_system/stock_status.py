from shared.helpers.db_helpers import TypeClassBase


class StockStatus(TypeClassBase):

    orphaned = 'orphaned'
    in_stock = 'in_stock'
    with_user = 'with_user'
    installed = 'installed'
    lost = 'lost'

    _human_codes = {
        orphaned: 'Orphaned',
        in_stock: 'In Stock',
        with_user: 'With User',
        installed: 'Installed',
        lost: 'Lost'
    }


class StockMovementStatus(TypeClassBase):

    pending = 'pending'
    accepted = 'accepted'
    rejected = 'rejected'

    _human_codes = {
        pending: 'Pending',
        accepted: 'Accepted',
        rejected: 'Rejected'
    }
