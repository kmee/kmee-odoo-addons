# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.exceptions import AccessError
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
            # all leads: the record rules let them read the orders of others
            cls.env.ref("sales_team.group_sale_salesman_all_leads").id,
        ]
        cls.cost_group = cls.env.ref("product_cost_security.group_product_cost")
        cls.salesman = cls._create_user("margin_salesman", base_groups)
        cls.cost_user = cls._create_user(
            "margin_cost_user", base_groups + [cls.cost_group.id]
        )
        cls.partner = cls.env["res.partner"].create({"name": "Margin customer"})
        cls.product = cls.env["product.product"].create(
            {"name": "Margin product", "list_price": 100.0, "standard_price": 60.0}
        )
        cls.order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [
                    (0, 0, {"product_id": cls.product.id, "product_uom_qty": 2.0})
                ],
            }
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

    def _expected_margin(self, order):
        lines = order.sudo().order_line
        return sum(lines.mapped("price_subtotal")) - sum(
            line.purchase_price * line.product_uom_qty for line in lines
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

    def test_margin_hidden_without_cost_group(self):
        """
        Given a salesman without the product cost group
        When the sale order form is rendered
        Then the margin is stripped too (cost = subtotal - margin)
        """
        arch = (
            self.env["sale.order"]
            .with_user(self.salesman)
            .get_view(view_type="form")["arch"]
        )
        self.assertFalse(etree.fromstring(arch).xpath("//field[@name='margin']"))

    def test_cost_fields_unreadable_by_orm_without_cost_group(self):
        """
        Given a salesman without the product cost group
        When he reads the cost and margin of an order by RPC/ORM
        Then the server refuses each field, on the line and on the order
        """
        line = self.order.order_line.with_user(self.salesman)
        order = self.order.with_user(self.salesman)
        # control: the rest of the line and of the order stays readable
        self.assertEqual(
            line.read(["price_subtotal"])[0]["price_subtotal"],
            self.order.order_line.price_subtotal,
        )
        self.assertTrue(order.read(["amount_untaxed"]))
        for fname in ("purchase_price", "margin", "margin_percent"):
            with self.assertRaises(AccessError, msg=fname):
                line.read([fname])
        for fname in ("margin", "margin_percent"):
            with self.assertRaises(AccessError, msg=fname):
                order.read([fname])
        with self.assertRaises(AccessError):
            line.write({"purchase_price": 1.0})

    def test_cost_fields_not_aggregated_without_cost_group(self):
        """
        Given a salesman without the product cost group
        When he groups lines, orders or the sales report asking for the margin
        Then the server refuses instead of returning the aggregated cost
        """
        cases = (
            ("sale.order.line", ["margin:sum"], ["order_id"]),
            ("sale.order.line", ["purchase_price"], ["order_id"]),
            ("sale.order", ["margin"], ["partner_id"]),
            ("sale.report", ["total:sum(margin)"], ["partner_id"]),
        )
        for model, fields, groupby in cases:
            with self.assertRaises(AccessError, msg=model):
                self.env[model].with_user(self.salesman).read_group([], fields, groupby)
        # control: other aggregates still work for him
        groups = (
            self.env["sale.order.line"]
            .with_user(self.salesman)
            .read_group([("order_id", "=", self.order.id)], ["price_subtotal"], [])
        )
        self.assertEqual(
            groups[0]["price_subtotal"], self.order.order_line.price_subtotal
        )
        # and an empty field list does not leak the cost either
        groups = (
            self.env["sale.order.line"]
            .with_user(self.salesman)
            .read_group([("order_id", "=", self.order.id)], [], ["order_id"])
        )
        self.assertNotIn("margin", groups[0])
        self.assertNotIn("purchase_price", groups[0])

    def test_cost_fields_readable_with_cost_group(self):
        """
        Given a user of the product cost group
        When he reads and groups the cost and margin
        Then he gets the values (negative control of the restriction)
        """
        line = self.order.order_line.with_user(self.cost_user)
        values = line.read(["purchase_price", "margin", "margin_percent"])[0]
        self.assertEqual(values["purchase_price"], 60.0)
        # other modules of the repository may change how the subtotal is
        # computed: the margin is checked against the subtotal, not a constant
        margin = self._expected_margin(self.order)
        self.assertAlmostEqual(values["margin"], margin)
        self.assertAlmostEqual(self.order.with_user(self.cost_user).margin, margin)
        groups = (
            self.env["sale.order.line"]
            .with_user(self.cost_user)
            .read_group([("order_id", "=", self.order.id)], ["margin:sum"], [])
        )
        self.assertAlmostEqual(groups[0]["margin"], margin)

    def test_salesman_flow_without_cost_group(self):
        """
        Given a salesman without the product cost group
        When he quotes, changes the quantity and confirms an order
        Then the flow works and the margin is still computed for the order
        """
        order = (
            self.env["sale.order"]
            .with_user(self.salesman)
            .create(
                {
                    "partner_id": self.partner.id,
                    "order_line": [
                        (0, 0, {"product_id": self.product.id, "product_uom_qty": 1.0})
                    ],
                }
            )
        )
        order.order_line.write({"product_uom_qty": 3.0})
        # confirming must not trip the cost restriction (other modules installed
        # in the same database may hold the order for validation, so the state
        # is not asserted here)
        order.action_confirm()
        self.assertAlmostEqual(order.sudo().margin, self._expected_margin(order))
