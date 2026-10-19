# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCustomPaymentTerm(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.Term = cls.env["account.payment.term"]
        cls.term = cls.Term.create(
            {
                "name": "50/50 30-60",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "value": "percent",
                            "value_amount": 50.0,
                            "nb_days": 30,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "value": "percent",
                            "value_amount": 50.0,
                            "nb_days": 60,
                        },
                    ),
                ],
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Custom Term Partner"})
        cls.product = cls.env["product.product"].create(
            {"name": "Service", "type": "service", "list_price": 100.0}
        )

    def _invoice(self, term=None):
        return self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_date": "2026-01-10",
                "invoice_payment_term_id": term.id if term else False,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "quantity": 1,
                            "price_unit": 100.0,
                        },
                    )
                ],
            }
        )

    def test_create_custom_term_is_archived(self):
        """Given a new term flagged custom, When created, Then it is archived.

        A normal term stays active (negative control).
        """
        custom = self.Term.create({"name": "Custom A", "is_custom": True})
        normal = self.Term.create({"name": "Normal"})
        self.assertTrue(custom.is_custom)
        self.assertFalse(custom.active)
        self.assertTrue(normal.active)
        self.assertFalse(normal.is_custom)

    def test_batch_create_archives_only_custom(self):
        """Given a batch of two terms (one custom), When created together,
        Then only the custom one is archived (create must be multi-record safe)."""
        terms = self.Term.create(
            [
                {"name": "Batch custom", "is_custom": True},
                {"name": "Batch normal"},
            ]
        )
        self.assertEqual(len(terms), 2)
        self.assertFalse(terms[0].active)
        self.assertTrue(terms[1].active)

    def test_custom_term_hidden_from_default_search(self):
        """Given a custom term, When searching terms, Then it is not listed
        unless archived records are requested."""
        custom = self.Term.create({"name": "Hidden custom", "is_custom": True})
        self.assertNotIn(custom, self.Term.search([("name", "=", "Hidden custom")]))
        found = self.Term.with_context(active_test=False).search(
            [("name", "=", "Hidden custom")]
        )
        self.assertEqual(found, custom)

    def test_write_is_custom_archives(self):
        """Given an active term, When flagged custom, Then it is archived."""
        term = self.Term.create({"name": "Later"})
        self.assertTrue(term.active)
        term.write({"is_custom": True})
        self.assertFalse(term.active)

    def test_write_is_custom_false_keeps_state(self):
        """Given an active normal term, When is_custom is written False,
        Then it is not archived."""
        term = self.Term.create({"name": "Stay"})
        term.write({"is_custom": False})
        self.assertTrue(term.active)

    def test_write_is_custom_only_archives_flagged_records(self):
        """Given two terms, When writing is_custom on one, Then only it is archived."""
        a = self.Term.create({"name": "A"})
        b = self.Term.create({"name": "B"})
        a.write({"is_custom": True})
        self.assertFalse(a.active)
        self.assertTrue(b.active)

    def test_copy_term_as_custom(self):
        """Given a term with two lines, When copying it as custom, Then the copy
        is custom, archived, renamed, keeps the lines and leaves the source intact."""
        custom = self.term.copy_term_id_as_custom(name="Custom X")
        self.assertNotEqual(custom, self.term)
        self.assertTrue(custom.is_custom)
        self.assertFalse(custom.active)
        self.assertEqual(custom.name, "Custom X")
        self.assertEqual(len(custom.line_ids), 2)
        self.assertEqual(
            sorted(custom.line_ids.mapped("nb_days")),
            sorted(self.term.line_ids.mapped("nb_days")),
        )
        self.assertFalse(self.term.is_custom)
        self.assertTrue(self.term.active)
        self.assertEqual(self.term.name, "50/50 30-60")

    def test_copy_term_as_custom_default_name(self):
        """When no name is given, Then the copy is called 'Custom'."""
        self.assertEqual(self.term.copy_term_id_as_custom().name, "Custom")

    def test_copy_term_as_custom_requires_single_record(self):
        """Given two terms, When copying as custom, Then ensure_one fails."""
        other = self.Term.create({"name": "Other"})
        with self.assertRaises(ValueError):
            (self.term | other).copy_term_id_as_custom()

    def test_move_new_custom_term_from_current(self):
        """Given an invoice with a term, When asking for a custom copy,
        Then the invoice points to an archived custom copy named after it."""
        move = self._invoice(self.term)
        move.action_post()
        move.action_new_custom_term_from_current()
        new_term = move.invoice_payment_term_id
        self.assertNotEqual(new_term, self.term)
        self.assertTrue(new_term.is_custom)
        self.assertFalse(new_term.active)
        self.assertEqual(new_term.name, "Custom: %s" % move.name)
        self.assertEqual(len(new_term.line_ids), 2)

    def test_move_custom_term_is_editable_without_touching_original(self):
        """Given an invoice using a custom copy, When editing the copy lines,
        Then the shared original term keeps its definition."""
        move = self._invoice(self.term)
        move.action_new_custom_term_from_current()
        custom = move.invoice_payment_term_id
        custom.line_ids.filtered(lambda line: line.nb_days == 60).nb_days = 90
        self.assertEqual(max(custom.line_ids.mapped("nb_days")), 90)
        self.assertEqual(max(self.term.line_ids.mapped("nb_days")), 60)

    def test_move_new_custom_term_without_term_raises(self):
        """Given an invoice without payment term, When asking for a custom copy,
        Then a UserError is raised."""
        move = self._invoice()
        with self.assertRaises(UserError):
            move.action_new_custom_term_from_current()
