# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.tests import Form, TransactionCase, new_test_user, tagged


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
        self.assertIn("can_edit_price_purchase", nodes[0].get("readonly", ""))
        list_node = root.xpath("//field[@name='order_line']/list")[0]
        self.assertIsNone(list_node.get("editable"))
        # control: without this module the core tree is editable inline
        core = etree.fromstring(self.env.ref("purchase.purchase_order_form").arch_db)
        core_list = core.xpath("//field[@name='order_line']/list")[0]
        self.assertEqual(core_list.get("editable"), "bottom")

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
