# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCustomPaymentTerm(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.term = cls.env.ref("account.account_payment_term_30days")

    def test_create_custom_is_archived(self):
        term = self.env["account.payment.term"].create(
            {"name": "Custom A", "is_custom": True}
        )
        self.assertFalse(term.active)
        normal = self.env["account.payment.term"].create({"name": "Normal"})
        self.assertTrue(normal.active)

    def test_write_custom_archives(self):
        term = self.env["account.payment.term"].create({"name": "Later"})
        term.write({"is_custom": True})
        self.assertFalse(term.active)

    def test_copy_term_as_custom(self):
        custom = self.term.copy_term_id_as_custom(name="Custom X")
        self.assertTrue(custom.is_custom)
        self.assertFalse(custom.active)
        self.assertEqual(custom.name, "Custom X")

    def test_move_new_custom_term(self):
        move = self.env["account.move"].create(
            {"move_type": "out_invoice", "invoice_payment_term_id": self.term.id}
        )
        move.action_new_custom_term_from_current()
        self.assertTrue(move.invoice_payment_term_id.is_custom)
        move.invoice_payment_term_id = False
        with self.assertRaises(UserError):
            move.action_new_custom_term_from_current()
