from stock_management_system.stock_status import StockStatus
from pony import orm

class StockItemFilterService:

    @classmethod
    def filter_by_tags(cls, items, tags):
        if not tags:
            return items
        first = True
        devices_with_tags_ids = []
        for tag in tags:
            devices_with_new_tag = set(orm.select(d.id for d in tag.devices)[:])
            if not first:
                devices_with_tags_ids = devices_with_tags_ids.intersection(devices_with_new_tag)
            else:
                devices_with_tags_ids = devices_with_new_tag
                first = False
        return items.filter(lambda s: s.device.id in devices_with_tags_ids)

    @classmethod
    def filter(cls, stock_items, search='', product_type=None, status='',
                 stock_user=None, stock_client=None, stock_shop=None, product_sub_type=None):

        if search != '':
            stock_items = stock_items.filter(
                lambda item: search.lower() in (
                    item.device.composed_serial
                ).lower()
            )

        if product_type:
            stock_items = stock_items.filter(
                lambda item: item.device.type == product_type)
        
        if product_sub_type:
            stock_items = stock_items.filter(
                lambda item: item.device.product_sub_type.id == product_sub_type)

        if status:
            if stock_user and status == StockStatus.with_user:
                stock_items = stock_items.filter(
                    lambda item: stock_user.lower() in (
                        item.user.person.name
                        + ' ' + item.user.person.surname
                        + ' ' + str(item.user.id)
                    ).lower()
                )
            elif stock_client and status == StockStatus.installed:
                stock_items = stock_items.filter(
                    lambda item: stock_client.lower() in (
                        item.client.person.name
                        + ' ' + item.client.person.surname
                        + ' ' + str(item.client.id)
                    ).lower()
                )
            elif stock_shop and status == StockStatus.in_stock:
                stock_items = stock_items.filter(
                    lambda item: item.shop.id == stock_shop)
            else:
                stock_items = stock_items.filter(
                    lambda item: item.status == status)

        return stock_items



    @classmethod
    def filter_by_product_model(cls, stock_items, product_sub_type):
        if not product_sub_type:
            return stock_items
        return stock_items.filter(lambda item: item.device.product_sub_type == product_sub_type)