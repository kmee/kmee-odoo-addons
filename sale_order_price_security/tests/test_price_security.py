# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSaleOrderPriceSecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        group_ids = [
            cls.env.ref("base.group_user").id,
            cls.env.ref("sales_team.group_sale_salesman").id,
        ]
        cls.user = cls.env["res.users"].create(
            {
                "name": "Salesman",
                "login": "price_security_salesman",
                "group_ids": [(6, 0, group_ids)],
            }
        )
        product = cls.env["product.product"].create({"name": "Product"})
        order = cls.env["sale.order"].create(
            {
                "partner_id": cls.env["res.partner"].create({"name": "Customer"}).id,
                "order_line": [(0, 0, {"product_id": product.id})],
            }
        )
        cls.line = order.order_line

    def test_cannot_edit_price_without_group(self):
        self.assertFalse(self.line.with_user(self.user).can_edit_price_sale)

    def test_can_edit_price_with_group(self):
        self.user.write(
            {
                "group_ids": [
                    (
                        4,
                        self.env.ref(
                            "sale_order_price_security.group_sale_order_price_editor"
                        ).id,
                    )
                ]
            }
        )
        self.assertTrue(self.line.with_user(self.user).can_edit_price_sale)
