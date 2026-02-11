from shared.services.sorter import Sorter
from payg_loan_system.contracts.models.addons_model import ContractAddOn
from pony import orm


class AddonSorter(Sorter):
    def sort_by(field_name):
        options = {
        }
        return options.get(field_name, lambda a: ContractAddOn.id)

    def real_field_sort(field_name, desc=False):
        options = {
            'id': ContractAddOn.id,
            'reference': ContractAddOn.reference,
            'offer': lambda a: a.offer_version.offer.name,
            'client': lambda a: a.contract.client.full_name,
            'contract': lambda a: a.contract.reference,
            'total_value': ContractAddOn.total_amount,
            'time_paid': lambda a: orm.coalesce(a.time_paid, a.time_created),
            'already_paid': lambda a: a.already_paid,
            'unit_price': lambda a: a.offer_version.price,
            'time_cancelled': ContractAddOn.time_canceled,
            'time_created': ContractAddOn.time_created,
            'quantity_sold': ContractAddOn.quantity_sold,
            'sold_by': ContractAddOn.sale_made_by,
            'approved_by': ContractAddOn.sale_approved_by,
            'status': lambda a: a.status,
        }
        options_desc = {
            'offer': lambda a: orm.desc(a.offer_version.offer.name),
            'client': lambda a: orm.desc(a.contract.client.full_name),
            'contract': lambda a: orm.desc(a.contract.reference),
            'already_paid': lambda a: orm.desc(a.already_paid),
            'unit_price': lambda a: orm.desc(a.offer_version.price),
            'status': lambda a: orm.desc(a.status),
            'time_paid': lambda a: orm.desc(orm.coalesce(a.time_paid, a.time_created)),
        }
        if desc:
            return options_desc.get(field_name, options.get(field_name, lambda a: orm.desc(a.reference)))
        return options.get(field_name, lambda a: a.reference)
