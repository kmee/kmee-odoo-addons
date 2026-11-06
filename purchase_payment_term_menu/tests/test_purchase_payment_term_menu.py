# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestPurchasePaymentTermMenu(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.buyer = new_test_user(
            cls.env,
            login="pptm_buyer",
            groups="base.group_user,"
            "purchase_payment_term_menu.group_purchase_payment_term_manager",
        )
        cls.buyer_plain = new_test_user(
            cls.env,
            login="pptm_buyer_plain",
            groups="base.group_user,purchase.group_purchase_user",
        )
        cls.outsider = new_test_user(
            cls.env, login="pptm_outsider", groups="base.group_user"
        )
        cls.menu = cls.env.ref("purchase_payment_term_menu.menu_purchase_payment_term")

    def _term_vals(self, name="PPTM 30 days"):
        return {
            "name": name,
            "line_ids": [
                (0, 0, {"value": "percent", "value_amount": 100.0, "nb_days": 30})
            ],
        }

    def test_buyer_can_create_and_write(self):
        term = (
            self.env["account.payment.term"]
            .with_user(self.buyer)
            .create(self._term_vals())
        )
        self.assertEqual(len(term.line_ids), 1)
        term.write({"name": "PPTM 45 days"})
        term.line_ids.write({"nb_days": 45})
        self.assertEqual(term.line_ids.nb_days, 45)

    def test_buyer_cannot_unlink(self):
        term = self.env["account.payment.term"].create(self._term_vals())
        with self.assertRaises(AccessError):
            term.with_user(self.buyer).unlink()
        with self.assertRaises(AccessError):
            term.line_ids.with_user(self.buyer).unlink()

    def test_outsider_cannot_write(self):
        term = self.env["account.payment.term"].create(self._term_vals())
        with self.assertRaises(AccessError):
            term.with_user(self.outsider).write({"name": "Nope"})

    def test_menu_visibility(self):
        Menu = self.env["ir.ui.menu"]
        self.assertIn(self.menu.id, Menu.with_user(self.buyer)._visible_menu_ids())
        self.assertNotIn(
            self.menu.id, Menu.with_user(self.outsider)._visible_menu_ids()
        )

    def test_parent_and_menu_visible_with_group(self):
        """The parent menu must be visible too, or the entry is unreachable."""
        parent = self.env.ref("purchase.menu_purchase_config")
        visible = self.env["ir.ui.menu"].with_user(self.buyer)._visible_menu_ids()
        self.assertIn(parent.id, visible)
        self.assertIn(self.menu.id, visible)

    def test_plain_buyer_has_no_access_nor_menu(self):
        Term = self.env["account.payment.term"]
        with self.assertRaises(AccessError):
            Term.with_user(self.buyer_plain).create(self._term_vals("PPTM plain"))
        term = Term.create(self._term_vals())
        with self.assertRaises(AccessError):
            term.with_user(self.buyer_plain).write({"name": "Nope"})
        Menu = self.env["ir.ui.menu"]
        self.assertNotIn(
            self.menu.id, Menu.with_user(self.buyer_plain)._visible_menu_ids()
        )
        parent = self.env.ref("purchase.menu_purchase_config")
        self.assertNotIn(
            parent.id, Menu.with_user(self.buyer_plain)._visible_menu_ids()
        )

    def test_group_is_an_extra_right(self):
        """The Purchase None/User/Administrator selection stays untouched."""
        group = self.env.ref(
            "purchase_payment_term_menu.group_purchase_payment_term_manager"
        )
        self.assertEqual(
            group.category_id, self.env.ref("base.module_category_usability")
        )
        purchase_groups = self.env["res.groups"].search(
            [
                (
                    "category_id",
                    "=",
                    self.env.ref("base.module_category_inventory_purchase").id,
                )
            ]
        )
        self.assertNotIn(group, purchase_groups)

    def test_no_default_change(self):
        group = self.env.ref(
            "purchase_payment_term_menu.group_purchase_payment_term_manager"
        )
        # no group implies the new one, and nobody has it by default
        self.assertFalse(
            self.env["res.groups"].search([("implied_ids", "in", group.ids)])
        )
        self.assertEqual(group.users, self.buyer)
        # the only access rows created by this module belong to the new group
        data = self.env["ir.model.data"].search(
            [
                ("module", "=", "purchase_payment_term_menu"),
                ("model", "=", "ir.model.access"),
            ]
        )
        accesses = self.env["ir.model.access"].browse(data.mapped("res_id"))
        self.assertEqual(len(accesses), 2)
        self.assertEqual(accesses.group_id, group)
        self.assertFalse(accesses.filtered("perm_unlink"))
