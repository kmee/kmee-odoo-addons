# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPurchaseOrderPriceSecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        group_ids = [
            cls.env.ref("base.group_user").id,
            cls.env.ref("purchase.group_purchase_user").id,
        ]
        cls.user = cls.env["res.users"].create(
            {
                "name": "Buyer",
                "login": "price_security_buyer",
                "group_ids": [(6, 0, group_ids)],
            }
        )
        product = cls.env["product.product"].create({"name": "Product"})
        order = cls.env["purchase.order"].create(
            {
                "partner_id": cls.env["res.partner"].create({"name": "Vendor"}).id,
                "order_line": [(0, 0, {"product_id": product.id, "product_qty": 1.0})],
            }
        )
        cls.line = order.order_line

    def test_cannot_edit_price_without_group(self):
        self.assertFalse(self.line.with_user(self.user).can_edit_price_purchase)

    def test_can_edit_price_with_group(self):
        group = self.env.ref(
            "purchase_order_price_security.group_purchase_order_price_editor"
        )
        self.user.write({"group_ids": [(4, group.id)]})
        self.assertTrue(self.line.with_user(self.user).can_edit_price_purchase)
