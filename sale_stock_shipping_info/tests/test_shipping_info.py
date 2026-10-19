# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestShippingInfo(TransactionCase):
    def test_weight_and_volume_are_summed(self):
        product = self.env["product.product"].create(
            {"name": "Heavy", "weight": 2.0, "volume": 0.5}
        )
        order = self.env["sale.order"].create(
            {
                "partner_id": self.env["res.partner"].create({"name": "Customer"}).id,
                "order_line": [
                    (0, 0, {"product_id": product.id, "product_uom_qty": 3.0})
                ],
            }
        )
        self.assertEqual(order.shipping_weight, 6.0)
        self.assertEqual(order.shipping_volume, 1.5)
        order.order_line.product_uom_qty = 4.0
        self.assertEqual(order.shipping_weight, 8.0)

    def test_unit_names(self):
        order = self.env["sale.order"].create(
            {"partner_id": self.env["res.partner"].create({"name": "Customer"}).id}
        )
        self.assertTrue(order.weight_uom_name)
        self.assertTrue(order.volume_uom_name)
        self.assertTrue(order.dimension_uom_name)
