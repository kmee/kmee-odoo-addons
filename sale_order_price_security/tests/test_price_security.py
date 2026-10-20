# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.tests import Form, TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestSaleOrderPriceSecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.editor_group = cls.env.ref(
            "sale_order_price_security.group_sale_order_price_editor"
        )
        base_groups = "base.group_user,sales_team.group_sale_salesman_all_leads"
        cls.salesman = new_test_user(
            cls.env, login="price_sec_salesman", groups=base_groups
        )
        cls.editor = new_test_user(
            cls.env,
            login="price_sec_editor",
            groups=base_groups
            + ",sale_order_price_security.group_sale_order_price_editor",
        )
        cls.partner = cls.env["res.partner"].create({"name": "Customer"})
        cls.product = cls.env["product.product"].create(
            {"name": "Product", "list_price": 100.0}
        )
        cls.order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [
                    (0, 0, {"product_id": cls.product.id, "product_uom_qty": 1.0}),
                    (0, 0, {"product_id": cls.product.id, "product_uom_qty": 2.0}),
                ],
            }
        )

    def test_group_is_not_implied_by_sales_groups(self):
        """
        Given the price editor group created by the module
        When we look at the plain salesman user
        Then he is not a member, while the editor user is
        """
        self.assertNotIn(self.editor_group, self.salesman.groups_id)
        self.assertIn(self.editor_group, self.editor.groups_id)

    def test_cannot_edit_price_without_group(self):
        """
        Given a salesman outside the price editor group
        When he reads the flag of every line of an order
        Then can_edit_price_sale is False for all of them
        """
        lines = self.order.order_line.with_user(self.salesman)
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines.mapped("can_edit_price_sale"), [False, False])

    def test_can_edit_price_with_group(self):
        """
        Given a user that belongs to the price editor group
        When he reads the flag of every line of an order
        Then can_edit_price_sale is True for all of them
        """
        lines = self.order.order_line.with_user(self.editor)
        self.assertEqual(lines.mapped("can_edit_price_sale"), [True, True])

    def test_flag_follows_group_membership(self):
        """
        Given a salesman reading the flag as False
        When he is added to the price editor group
        Then the flag, read in a fresh environment, becomes True
        """
        line = self.order.order_line[0]
        self.assertFalse(line.with_user(self.salesman).can_edit_price_sale)
        self.salesman.write({"groups_id": [(4, self.editor_group.id)]})
        self.assertTrue(line.with_user(self.salesman).can_edit_price_sale)

    def test_product_onchange_refreshes_flag_for_current_user(self):
        """
        Given a new order line built by a salesman and by an editor
        When the product onchange runs
        Then the flag reflects the group of the user running it
        """
        for user, expected in ((self.salesman, False), (self.editor, True)):
            line = (
                self.env["sale.order.line"]
                .with_user(user)
                .new({"order_id": self.order.id, "product_id": self.product.id})
            )
            line.product_id_change()
            self.assertEqual(line.can_edit_price_sale, expected, user.login)

    def _line_nodes(self, user):
        arch = (
            self.env["sale.order"]
            .with_user(user)
            .get_view(self.env.ref("sale.view_order_form").id, "form")["arch"]
        )
        root = etree.fromstring(arch)
        return root.xpath(
            "//field[@name='order_line']/*[self::form or self::list]"
            "//field[@name='price_unit']"
        )

    def test_views_make_price_unit_depend_on_flag(self):
        """
        Given the sale order form view
        When we inspect price_unit in the line tree and in the line form
        Then both are readonly when can_edit_price_sale is False
        """
        nodes = self._line_nodes(self.salesman)
        self.assertEqual(len(nodes), 2)
        for node in nodes:
            self.assertIn("can_edit_price_sale", node.get("readonly", ""))
        # control: the core view alone has no such rule
        core = self.env.ref("sale.view_order_form").arch_db
        self.assertNotIn("can_edit_price_sale", core)

    def test_form_blocks_price_edit_without_group(self):
        """
        Given a salesman outside the group editing a line in the form
        When he tries to change the unit price
        Then the Form refuses (readonly) and the price stays at the list price
        """
        with Form(self.order.with_user(self.salesman)) as form:
            with form.order_line.edit(0) as line:
                with self.assertRaises(AssertionError):
                    line.price_unit = 1.0
                self.assertEqual(line.price_unit, 100.0)

    def test_form_allows_price_edit_with_group(self):
        """
        Given a user of the price editor group editing a line in the form
        When he changes the unit price and saves
        Then the new price is stored on the line
        """
        with Form(self.order.with_user(self.editor)) as form:
            with form.order_line.edit(0) as line:
                line.price_unit = 55.0
        self.assertEqual(self.order.order_line[0].price_unit, 55.0)
