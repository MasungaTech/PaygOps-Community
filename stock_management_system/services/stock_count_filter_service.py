from stock_management_system.stock_status import StockStatus

class StockCountFilterService:
    @staticmethod
    def filter(stock_counts, entity_id=None, child_entity_id=None, **additional_params):
        if entity_id is not None:
            stock_counts = [sc for sc in stock_counts if sc['entity']['id'] == entity_id]

        if child_entity_id is not None:
            stock_counts = [sc for sc in stock_counts if any(child['id'] == child_entity_id for child in sc['entity']['children'])]

        for status in StockStatus.to_list():
            if status in additional_params and additional_params[status]:
                stock_counts = [sc for sc in stock_counts if sc['counts'].get(status) == additional_params[status]]

        for key, value in additional_params.items():
            if value and key not in StockStatus.to_list():
                stock_counts = [sc for sc in stock_counts if sc.get(key) == value]
        return stock_counts
