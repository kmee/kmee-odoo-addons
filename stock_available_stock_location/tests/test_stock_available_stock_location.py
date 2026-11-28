# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestStockAvailableStockLocation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.stock = cls.warehouse.lot_stock_id
        cls.shelf = cls.env["stock.location"].create(
            {"name": "Prateleira", "location_id": cls.stock.id}
        )
        cls.dock = cls.env["stock.location"].create(
            {"name": "Doca", "location_id": cls.warehouse.view_location_id.id}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Produto", "type": "consu", "is_storable": True}
        )
        Quant = cls.env["stock.quant"]
        Quant._update_available_quantity(cls.product, cls.stock, 10)
        Quant._update_available_quantity(cls.product, cls.shelf, 5)
        Quant._update_available_quantity(cls.product, cls.dock, 7)

    def test_only_stock_location_and_children(self):
        self.assertEqual(self.product.qty_available, 22)
        self.assertEqual(self.product.qty_available_stock, 15)
        self.assertEqual(self.product.product_tmpl_id.qty_available_stock, 15)

    def test_action_filters_quants(self):
        action = self.product.action_open_stock_quants()
        quants = self.env["stock.quant"].search(action["domain"])
        self.assertEqual(quants.location_id, self.stock | self.shelf)
