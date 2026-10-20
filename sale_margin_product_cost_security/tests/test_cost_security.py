# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSaleMarginCostSecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(cls.env.context, tracking_disable=True, no_reset_password=True)
        )
        base_groups = [
            cls.env.ref("base.group_user").id,
            cls.env.ref("sales_team.group_sale_salesman").id,
        ]
        cls.cost_group = cls.env.ref("product_cost_security.group_product_cost")
        cls.salesman = cls._create_user("margin_salesman", base_groups)
        cls.cost_user = cls._create_user(
            "margin_cost_user", base_groups + [cls.cost_group.id]
        )

    @classmethod
    def _create_user(cls, login, group_ids):
        return (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": login,
                    "login": login,
                    "email": "%s@example.com" % login,
                    "groups_id": [(6, 0, group_ids)],
                }
            )
        )

    def _cost_nodes(self, user):
        """Return {"form": n, "tree": n}: purchase_price nodes inside order lines."""
        arch = self.env["sale.order"].with_user(user).get_view(view_type="form")["arch"]
        tree = etree.fromstring(arch)
        return {
            kind: len(
                tree.xpath(
                    "//field[@name='order_line']/%s//field[@name='purchase_price']"
                    % kind
                )
            )
            for kind in ("form", "tree")
        }

    def test_purchase_price_hidden_without_cost_group(self):
        """
        Given a salesman without the product cost group
        When the sale order form is rendered
        Then the purchase_price (cost) is stripped from the line form and list
        """
        self.assertNotIn(self.cost_group, self.salesman.groups_id)
        self.assertEqual(self._cost_nodes(self.salesman), {"form": 0, "tree": 0})

    def test_purchase_price_visible_with_cost_group(self):
        """
        Given a user that belongs to the product cost group
        When the sale order form is rendered
        Then the purchase_price (cost) is present in the line form and list
        """
        self.assertIn(self.cost_group, self.cost_user.groups_id)
        self.assertEqual(self._cost_nodes(self.cost_user), {"form": 1, "tree": 1})

    def test_margin_visible_for_salesman_without_cost_group(self):
        """
        Given a salesman without the product cost group
        When the sale order form is rendered
        Then the margin is still available (only the cost is protected)
        """
        arch = (
            self.env["sale.order"]
            .with_user(self.salesman)
            .get_view(view_type="form")["arch"]
        )
        self.assertTrue(etree.fromstring(arch).xpath("//field[@name='margin']"))
