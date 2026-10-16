from pony.orm import select

from stock_management_system.models import StockItem
from stock_management_system.quantity_stock_models import QuantityStockLocation
from stock_management_system.stock_status import StockStatus


class StockCountService:

    @classmethod
    def _get_entities(cls, entity, children=False):
        return entity.descendants.select(lambda e: e != entity) if children else [entity]

    @classmethod
    def _get_items_by_entities(cls, pst, status, entities):
        if status == StockStatus.in_stock:
            items = StockItem.select(lambda si: si.shop in entities)
        elif status == StockStatus.with_user:
            items = StockItem.select(lambda si: si.user.shop in entities)
        elif status == StockStatus.installed:
            items = StockItem.select(lambda si: si.client.person.village in entities)
        else:
            items = StockItem.select()
        return items.filter(
            lambda si: si.device.product_sub_type == pst and si.status == status
        ).count()

    @classmethod
    def _get_quantities_by_entities(cls, pst, status, entities):
        if status == StockStatus.in_stock:
            items = QuantityStockLocation.select(lambda qsl: qsl.operational_entity in entities)
        elif status == StockStatus.with_user:
            items = QuantityStockLocation.select(lambda qsl: qsl.user.shop in entities)
        elif status == StockStatus.installed:
            items = QuantityStockLocation.select(
                lambda qsl: qsl.addon.contract.client.person.village in entities
            )
        else:
            items = QuantityStockLocation.select()
        items = items.filter(lambda qsl: qsl.product_sub_type == pst and qsl.status == status)

        return select(qsl.total_quantity for qsl in items).sum()

    @classmethod
    def get_count(cls, pst, entity, status, children=False):
        entities = cls._get_entities(entity, children)
        items = cls._get_items_by_entities(pst, status, entities)
        quantities = cls._get_quantities_by_entities(pst, status, entities)
        return items + quantities

    @classmethod
    def get_total_count(cls, pst, status):
        items = StockItem.select(
            lambda si: si.status == status
            and si.device.product_sub_type == pst
        ).count()
        quantities = select(
            qsl.total_quantity for qsl in QuantityStockLocation if qsl.status == status
            and qsl.product_sub_type == pst
        ).sum()
        return items + quantities
