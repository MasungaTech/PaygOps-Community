from tests.base_test import BaseViewTest


class TestStockItemListView(BaseViewTest):
    url = 'stock.stock_list'
    template = 'stock_list.html'


class TestStockMovementListView(BaseViewTest):
    url = 'stock.stock_movements'
    template = 'stock_movements.html'


class TestAddStockMovementView(BaseViewTest):
    url = 'stock.add_movements'
    template = 'add_movements.html'
