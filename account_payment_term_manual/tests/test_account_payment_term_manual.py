# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date

from odoo.tests import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAccountPaymentTermManual(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.term = cls.env["account.payment.term"].create(
            {
                "name": "50% in 30 days, balance in 60 days",
                "line_ids": [
                    (0, 0, {"value": "percent", "value_amount": 50.0, "days": 30}),
                    (0, 0, {"value": "balance", "days": 60}),
                ],
            }
        )
        cls.customer = cls.env["res.partner"].create({"name": "Customer"})
        cls.product = cls.env["product.product"].create(
            {"name": "Product", "list_price": 1000.0}
        )

    def _invoice(self, with_manual_term=True):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.customer.id,
                "invoice_date": date(2024, 1, 15),
                "invoice_payment_term_id": self.term.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "quantity": 1,
                            "price_unit": 1000.0,
                            "tax_ids": False,
                        },
                    )
                ],
            }
        )
        if with_manual_term:
            invoice._update_manual_payment_term_id(self.term)
        return invoice

    def _installments(self, invoice):
        lines = invoice.line_ids.filtered(lambda x: x.display_type == "payment_term")
        return sorted((x.date_maturity, x.balance) for x in lines)

    def test_manual_term_copies_the_term(self):
        invoice = self._invoice()
        manual = invoice.manual_payment_term_id
        self.assertTrue(manual)
        self.assertEqual(manual.origin_term_id, self.term)
        self.assertFalse(manual.active)
        self.assertFalse(manual.has_manual_lines)
        self.assertEqual(
            sorted(manual.line_ids.mapped("days")),
            sorted(self.term.line_ids.mapped("days")),
        )
        self.assertEqual(
            sorted(manual.line_ids.mapped("value_amount")),
            sorted(self.term.line_ids.mapped("value_amount")),
        )

    def test_unedited_manual_term_uses_original_term(self):
        invoice = self._invoice()
        invoice.recompute_payment_lines()
        self.assertEqual(
            self._installments(invoice),
            [(date(2024, 2, 14), 500.0), (date(2024, 3, 15), 500.0)],
        )

    def test_edited_manual_term_changes_installments(self):
        invoice = self._invoice()
        manual = invoice.manual_payment_term_id
        percent = manual.line_ids.filtered(lambda x: x.value == "percent")
        balance = manual.line_ids.filtered(lambda x: x.value == "balance")
        percent.write({"value_amount": 30.0, "fixed_date": date(2024, 2, 20)})
        balance.write({"fixed_date": date(2024, 4, 10)})
        self.assertTrue(manual.has_manual_lines)
        self.assertTrue(manual.name.endswith("(edited)"))
        invoice.recompute_payment_lines()
        self.assertEqual(
            self._installments(invoice),
            [(date(2024, 2, 20), 300.0), (date(2024, 4, 10), 700.0)],
        )
        # the original term is untouched
        self.assertEqual(sorted(self.term.line_ids.mapped("value_amount")), [0.0, 50.0])
        invoice.action_post()
        self.assertEqual(
            sorted(invoice.line_ids.filtered("date_maturity").mapped("date_maturity")),
            [date(2024, 2, 20), date(2024, 4, 10)],
        )
        # the due date of the invoice is the last maturity, as in the core
        self.assertEqual(invoice.invoice_date_due, date(2024, 4, 10))

    def test_posted_invoice_keeps_total(self):
        invoice = self._invoice()
        manual = invoice.manual_payment_term_id
        manual.line_ids.filtered(lambda x: x.value == "percent").write(
            {"value_amount": 33.33}
        )
        invoice.recompute_payment_lines()
        invoice.action_post()
        total = sum(x[1] for x in self._installments(invoice))
        self.assertAlmostEqual(total, 1000.0)
        self.assertEqual(self._installments(invoice)[0][1], 333.3)

    def test_line_due_date(self):
        manual = self.env["account.payment.term.manual"].create({"name": "Manual"})
        line = manual.line_ids
        self.assertEqual(len(line), 1)
        self.assertEqual(line.value, "balance")
        base = date(2024, 1, 15)
        self.assertEqual(line._get_due_date(base), base)
        line.write({"months": 1, "days": 5})
        self.assertEqual(line._get_due_date(base), date(2024, 2, 20))
        line.write({"end_month": True, "days_after": 10})
        self.assertEqual(line._get_due_date(base), date(2024, 3, 10))
        line.fixed_date = date(2024, 5, 1)
        self.assertEqual(line._get_due_date(base), date(2024, 5, 1))

    def test_change_term_replaces_manual_term(self):
        invoice = self._invoice()
        old_manual = invoice.manual_payment_term_id
        other = self.env["account.payment.term"].create(
            {"name": "Immediate", "line_ids": [(0, 0, {"value": "balance"})]}
        )
        invoice.invoice_payment_term_id = other
        invoice._update_manual_payment_term_id(other)
        self.assertEqual(invoice.manual_payment_term_id.origin_term_id, other)
        self.assertFalse(old_manual.exists())

    def test_unlink_manual_term(self):
        invoice = self._invoice()
        manual = invoice.manual_payment_term_id
        lines = manual.line_ids
        # an invoice with the payment term of the same id must not block the unlink
        manual.unlink()
        self.assertFalse(manual.exists())
        self.assertFalse(lines.exists())

    def test_form_sets_manual_term(self):
        form = Form(
            self.env["account.move"].with_context(default_move_type="out_invoice")
        )
        form.partner_id = self.customer
        form.invoice_date = date(2024, 1, 15)
        with form.invoice_line_ids.new() as line:
            line.product_id = self.product
        form.invoice_payment_term_id = self.term
        invoice = form.save()
        self.assertEqual(invoice.manual_payment_term_id.origin_term_id, self.term)
