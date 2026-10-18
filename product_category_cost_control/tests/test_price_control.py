# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPriceControl(TransactionCase):
    def test_category_option_is_stored(self):
        category = self.env["product.category"].create(
            {"name": "Controlled", "price_control_option": "include_all_taxes"}
        )
        self.assertEqual(category.price_control_option, "include_all_taxes")

    def test_price_unit_without_fiscal_operation(self):
        category = self.env["product.category"].create(
            {"name": "Controlled", "price_control_option": "include_all_taxes"}
        )
        product = self.env["product.product"].create(
            {"name": "Product", "categ_id": category.id}
        )
        warehouse = self.env["stock.warehouse"].search([], limit=1)
        move = self.env["stock.move"].create(
            {
                "product_id": product.id,
                "product_uom_qty": 2.0,
                "uom_id": product.uom_id.id,
                "location_id": self.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": warehouse.lot_stock_id.id,
            }
        )
        self.assertEqual(move._get_price_unit(), 0.0)
