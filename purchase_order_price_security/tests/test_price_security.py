# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.exceptions import AccessError
from odoo.tests.common import Form, TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestPurchaseOrderPriceSecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.editor_group = cls.env.ref(
            "purchase_order_price_security.group_purchase_order_price_editor"
        )
        # account invoice: ACL of models used by other modules in the line form
        groups = (
            "base.group_user,purchase.group_purchase_user,account.group_account_invoice"
        )
        cls.buyer = new_test_user(cls.env, login="price_sec_buyer", groups=groups)
        cls.editor = new_test_user(
            cls.env,
            login="price_sec_buyer_editor",
            groups=groups
            + ",purchase_order_price_security.group_purchase_order_price_editor",
        )
        cls.manager = new_test_user(
            cls.env,
            login="price_sec_buyer_manager",
            groups="base.group_user,purchase.group_purchase_manager,"
            "account.group_account_invoice",
        )
        cls.partner = cls.env["res.partner"].create({"name": "Vendor"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Product",
                "standard_price": 10.0,
                "supplier_taxes_id": [(5, 0, 0)],
            }
        )
        cls.order = cls.env["purchase.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "product_qty": 1.0,
                            "price_unit": 10.0,
                            "taxes_id": [(5, 0, 0)],
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "product_qty": 3.0,
                            "price_unit": 10.0,
                            "taxes_id": [(5, 0, 0)],
                        },
                    ),
                ],
            }
        )

    def test_group_membership_is_explicit(self):
        """
        Given the price editor group created by the module
        When we look at a plain buyer and at the editor user
        Then only the editor belongs to the group
        """
        self.assertNotIn(self.editor_group, self.buyer.groups_id)
        self.assertIn(self.editor_group, self.editor.groups_id)

    def test_cannot_edit_price_without_group(self):
        """
        Given a buyer outside the price editor group
        When he reads the flag of every line of an order
        Then can_edit_price_purchase is False for all of them
        """
        lines = self.order.order_line.with_user(self.buyer)
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines.mapped("can_edit_price_purchase"), [False, False])

    def test_can_edit_price_with_group(self):
        """
        Given a buyer that belongs to the price editor group
        When he reads the flag of every line of an order
        Then can_edit_price_purchase is True for all of them
        """
        lines = self.order.order_line.with_user(self.editor)
        self.assertEqual(lines.mapped("can_edit_price_purchase"), [True, True])

    def test_flag_follows_group_membership(self):
        """
        Given a buyer reading the flag as False
        When he is added to the price editor group
        Then the flag, read in a fresh environment, becomes True
        """
        line = self.order.order_line[0]
        self.assertFalse(line.with_user(self.buyer).can_edit_price_purchase)
        self.buyer.write({"groups_id": [(4, self.editor_group.id)]})
        self.assertTrue(line.with_user(self.buyer).can_edit_price_purchase)

    def _order_view_arch(self):
        arch = (
            self.env["purchase.order"]
            .with_user(self.buyer)
            .get_view(self.env.ref("purchase.purchase_order_form").id, "form")["arch"]
        )
        return etree.fromstring(arch)

    def test_form_price_unit_readonly_rule_and_tree_not_editable(self):
        """
        Given the purchase order form view
        When we inspect the order lines
        Then price_unit in the line form depends on the flag and the line tree
        is no longer editable inline (otherwise the rule could be bypassed)
        """
        root = self._order_view_arch()
        nodes = root.xpath(
            "//field[@name='order_line']/form//field[@name='price_unit']"
        )
        self.assertEqual(len(nodes), 1)
        self.assertIn("can_edit_price_purchase", nodes[0].get("modifiers", ""))
        tree = root.xpath("//field[@name='order_line']/tree")[0]
        self.assertIsNone(tree.get("editable"))
        # control: without this module the core tree is editable inline
        core = etree.fromstring(self.env.ref("purchase.purchase_order_form").arch_db)
        core_tree = core.xpath("//field[@name='order_line']/tree")[0]
        self.assertEqual(core_tree.get("editable"), "bottom")

    def test_form_blocks_price_edit_without_group(self):
        """
        Given a buyer outside the group editing a line in the form
        When he tries to change the unit price
        Then the Form refuses (readonly) and the price is unchanged
        """
        with Form(self.order.with_user(self.buyer)) as form:
            with form.order_line.edit(0) as line:
                with self.assertRaises(AssertionError):
                    line.price_unit = 1.0
                self.assertEqual(line.price_unit, 10.0)

    def test_form_allows_price_edit_with_group(self):
        """
        Given a buyer of the price editor group editing a line in the form
        When he changes the unit price and saves
        Then the new price is stored on the line
        """
        with Form(self.order.with_user(self.editor)) as form:
            with form.order_line.edit(0) as line:
                line.price_unit = 7.5
        self.assertEqual(self.order.order_line[0].price_unit, 7.5)

    def _line_vals(self, **kw):
        vals = {
            "order_id": self.order.id,
            "product_id": self.product.id,
            "product_qty": 1.0,
            "taxes_id": [(5, 0, 0)],
        }
        vals.update(kw)
        return vals

    def test_orm_write_of_price_refused_without_group(self):
        """
        Given a buyer outside the price editor group
        When he writes price_unit by RPC/ORM, on the line or through the order
        Then the server refuses and the price is unchanged
        """
        line = self.order.order_line[0]
        with self.assertRaises(AccessError):
            line.with_user(self.buyer).write({"price_unit": 1.0})
        with self.assertRaises(AccessError):
            self.order.with_user(self.buyer).write(
                {"order_line": [(1, line.id, {"price_unit": 1.0})]}
            )
        self.assertEqual(line.price_unit, 10.0)

    def test_orm_create_with_price_refused_without_group(self):
        """
        Given a buyer outside the price editor group
        When he creates a line or an order with a price of his own
        Then the server refuses
        """
        with self.assertRaises(AccessError):
            self.env["purchase.order.line"].with_user(self.buyer).create(
                self._line_vals(price_unit=99.0)
            )
        vals = self._line_vals(price_unit=99.0)
        del vals["order_id"]
        with self.assertRaises(AccessError):
            self.env["purchase.order"].with_user(self.buyer).create(
                {"partner_id": self.partner.id, "order_line": [(0, 0, vals)]}
            )

    def test_orm_price_allowed_with_group(self):
        """
        Given a buyer of the price editor group
        When he creates and writes lines with a price of his own by RPC/ORM
        Then the prices are stored (negative control of the restriction)
        """
        line = self.order.order_line[0]
        line.with_user(self.editor).write({"price_unit": 7.5})
        self.assertEqual(line.price_unit, 7.5)
        new_line = (
            self.env["purchase.order.line"]
            .with_user(self.editor)
            .create(self._line_vals(price_unit=99.0))
        )
        self.assertEqual(new_line.price_unit, 99.0)

    def test_purchase_manager_can_edit_price_buyer_cannot(self):
        """
        Given a purchase administrator (and the admin user) and a plain buyer
        When each one writes price_unit on a line by RPC/ORM
        Then the administrators store the price through the implied price
        editor group, while the buyer is still refused
        """
        admin = self.env.ref("base.user_admin")
        self.assertIn(self.editor_group, self.manager.groups_id)
        self.assertIn(self.editor_group, admin.groups_id)
        line = self.order.order_line[0]
        line.with_user(self.manager).write({"price_unit": 7.5})
        self.assertEqual(line.price_unit, 7.5)
        line.with_user(admin).write({"price_unit": 8.5})
        self.assertEqual(line.price_unit, 8.5)
        with self.assertRaises(AccessError):
            line.with_user(self.buyer).write({"price_unit": 1.0})
        self.assertEqual(line.price_unit, 8.5)

    def test_buyer_purchase_flow_keeps_working(self):
        """
        Given a buyer outside the price editor group
        When he creates an order, changes quantities, sends the computed
        price, adds a note, confirms and duplicates an order
        Then everything works and prices come from the vendor or the cost
        """
        order = (
            self.env["purchase.order"]
            .with_user(self.buyer)
            .create(
                {
                    "partner_id": self.partner.id,
                    "order_line": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.product.id,
                                "product_qty": 1.0,
                                "taxes_id": [(5, 0, 0)],
                            },
                        ),
                        # internal flows send the price the system computes
                        (
                            0,
                            0,
                            {
                                "product_id": self.product.id,
                                "product_qty": 2.0,
                                "price_unit": 10.0,
                                "taxes_id": [(5, 0, 0)],
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "display_type": "line_note",
                                "name": "A note",
                                "product_qty": 0.0,
                            },
                        ),
                    ],
                }
            )
        )
        line = order.order_line[0]
        self.assertEqual(line.price_unit, 10.0)
        line.write({"product_qty": 5.0, "price_unit": 10.0})
        order.button_confirm()
        self.assertEqual(order.state, "purchase")
        # an order priced by an editor is duplicated by the buyer: the copy
        # takes the computed price instead of the custom one
        self.order.order_line.with_user(self.editor).write({"price_unit": 7.5})
        copy = self.order.with_user(self.buyer).copy()
        self.assertEqual(copy.order_line.mapped("price_unit"), [10.0, 10.0])
        copy = self.order.with_user(self.editor).copy()
        self.assertEqual(copy.order_line.mapped("price_unit"), [7.5, 7.5])
