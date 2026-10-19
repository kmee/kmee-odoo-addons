# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSaleOrderLineQtyFields(TransactionCase):
    def test_free_qty_follows_product(self):
        product = self.env["product.product"].create(
            {"name": "Stored Product", "is_storable": True}
        )
        warehouse = self.env["stock.warehouse"].search([], limit=1)
        self.env["stock.quant"]._update_available_quantity(
            product, warehouse.lot_stock_id, 5.0
        )
        order = self.env["sale.order"].create(
            {
                "partner_id": self.env["res.partner"].create({"name": "Customer"}).id,
                "order_line": [(0, 0, {"product_id": product.id})],
            }
        )
        self.assertEqual(order.order_line.free_qty, product.free_qty)
        self.assertEqual(order.order_line.free_qty, 5.0)

    def test_settings_enable_groups(self):
        settings = self.env["res.config.settings"].create({"group_free_qty": True})
        settings.execute()
        group = self.env.ref("sale_order_line_qty_fields.group_free_qty")
        self.assertIn(group, self.env.ref("base.group_user").all_implied_ids)
