# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSaleMarginCostSecurity(TransactionCase):
    def _get_arch(self, group_xmlids):
        group_ids = [self.env.ref(x).id for x in group_xmlids]
        user = self.env["res.users"].create(
            {
                "name": "User %s" % len(group_xmlids),
                "login": "margin_cost_user_%s" % len(group_xmlids),
                "group_ids": [(6, 0, group_ids)],
            }
        )
        return self.env["sale.order"].with_user(user).get_view(view_type="form")["arch"]

    def test_purchase_price_hidden_without_cost_group(self):
        arch = self._get_arch(["base.group_user", "sales_team.group_sale_salesman"])
        self.assertNotIn('name="purchase_price"', arch)

    def test_purchase_price_visible_with_cost_group(self):
        arch = self._get_arch(
            [
                "base.group_user",
                "sales_team.group_sale_salesman",
                "product_cost_security.group_product_cost",
            ]
        )
        self.assertIn('name="purchase_price"', arch)
