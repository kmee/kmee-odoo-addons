# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.tests.common import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPaymentCurrencyRate(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.company
        cls.foreign = cls.env.ref("base.EUR")
        if cls.foreign == cls.company.currency_id:
            cls.foreign = cls.env.ref("base.USD")
        cls.foreign.active = True
        cls.env["res.currency.rate"].search(
            [("currency_id", "=", cls.foreign.id), ("company_id", "=", cls.company.id)]
        ).unlink()
        cls.env["res.currency.rate"].create(
            {
                "name": fields.Date.today(),
                "currency_id": cls.foreign.id,
                "company_id": cls.company.id,
                "rate": 0.5,
            }
        )
        # rate relative to the company currency (it may have its own rate)
        cls.base_rate = cls.foreign.rate
        cls.partner = cls.env["res.partner"].create({"name": "Rate Partner"})
        cls.product = cls.env["product.product"].create(
            {"name": "Rate Service", "type": "service"}
        )
        cls.profit = cls.env["account.account"].create(
            {
                "code": "RATE.P",
                "name": "FX Gain",
                "account_type": "income_other",
                "company_id": cls.company.id,
            }
        )
        cls.loss = cls.env["account.account"].create(
            {
                "code": "RATE.L",
                "name": "FX Loss",
                "account_type": "expense",
                "company_id": cls.company.id,
            }
        )
        cls.journal = cls.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", cls.company.id)], limit=1
        ) or cls.env["account.journal"].create(
            {
                "name": "Rate Bank",
                "type": "bank",
                "code": "RTBK",
                "company_id": cls.company.id,
            }
        )
        cls.journal.write(
            {"profit_account_id": cls.profit.id, "loss_account_id": cls.loss.id}
        )
        cls.invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.partner.id,
                "currency_id": cls.foreign.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "quantity": 1,
                            "price_unit": 100.0,
                            "tax_ids": [(5, 0, 0)],
                        },
                    )
                ],
            }
        )
        cls.invoice.action_post()

    def _form(self):
        ctx = {"active_model": "account.move", "active_ids": self.invoice.ids}
        form = Form(self.env["account.payment.register"].with_context(**ctx))
        form.journal_id = self.journal
        return form

    def test_original_rate_is_the_currency_rate(self):
        """Given an invoice in a foreign currency with a dated rate,
        When opening the payment wizard, Then original_rate is that rate and the
        manual rate starts equal to it (percent 1)."""
        form = self._form()
        # change_rate_percent is a readonly field in the view: read it from the
        # form (onchange result), it is not written on save.
        self.assertAlmostEqual(form.change_rate_percent, 1.0, places=4)
        wizard = form.save()
        self.assertEqual(wizard.currency_id, self.foreign)
        self.assertAlmostEqual(wizard.original_rate, self.base_rate, places=4)
        self.assertAlmostEqual(wizard.change_rate, self.base_rate, places=4)
        self.assertNotEqual(wizard.original_rate, 1.0)
        self.assertAlmostEqual(wizard.amount, 100.0, places=2)

    def test_untouched_rate_keeps_amount_and_handling(self):
        """Given the wizard without changing the rate,
        Then the amount stays and no write-off is configured."""
        wizard = self._form().save()
        self.assertAlmostEqual(wizard.amount, 100.0, places=2)
        self.assertEqual(wizard.payment_difference_handling, "open")
        self.assertNotEqual(wizard.writeoff_label, "Cambio")

    def test_rate_up_scales_amount_and_books_gain(self):
        """Given an original rate, When the user raises it 20%,
        Then percent is 1.2, amount is 120, difference is reconciled with the
        'Cambio' label on the profit account."""
        form = self._form()
        form.change_rate = self.base_rate * 1.2
        self.assertAlmostEqual(form.change_rate_percent, 1.2, places=4)
        wizard = form.save()
        self.assertAlmostEqual(wizard.amount, 120.0, places=2)
        self.assertEqual(wizard.payment_difference_handling, "reconcile")
        self.assertEqual(wizard.writeoff_label, "Cambio")
        self.assertEqual(wizard.writeoff_account_id, self.profit)

    def test_rate_down_scales_amount_and_books_loss(self):
        """Given an original rate, When the user lowers it 20%,
        Then percent is 0.8, amount is 80 and the loss account is used."""
        form = self._form()
        form.change_rate = self.base_rate * 0.8
        self.assertAlmostEqual(form.change_rate_percent, 0.8, places=4)
        wizard = form.save()
        self.assertAlmostEqual(wizard.amount, 80.0, places=2)
        self.assertEqual(wizard.payment_difference_handling, "reconcile")
        self.assertEqual(wizard.writeoff_account_id, self.loss)

    def test_change_rate_percent_formula(self):
        """Given an original rate, When change_rate is doubled,
        Then change_rate_percent = change_rate / original_rate = 2."""
        wizard = self._form().save()
        wizard.change_rate = wizard.original_rate * 2
        wizard.onchange_change_rate()
        self.assertAlmostEqual(wizard.change_rate_percent, 2.0, places=4)

    def test_onchange_original_rate_resets_change_rate(self):
        """Given a manually typed rate, When the currency rate onchange fires,
        Then the rate goes back to the currency rate."""
        wizard = self._form().save()
        wizard.change_rate = 5
        wizard.onchange_currency_id()
        self.assertAlmostEqual(wizard.change_rate, wizard.original_rate, places=4)

    def test_payment_with_rate_difference_reconciles_invoice(self):
        """Given the rate raised 20%, When creating the payment,
        Then the payment is for 120 and the invoice is fully paid because the
        difference was written off on the profit account with label 'Cambio'."""
        form = self._form()
        form.change_rate = self.base_rate * 1.2
        wizard = form.save()
        payments = wizard._create_payments()
        self.assertEqual(self.invoice.payment_state, "paid")
        self.assertAlmostEqual(payments.amount, 120.0, places=2)
        lines = payments.move_id.line_ids | self.invoice.line_ids
        fx_lines = lines.filtered(lambda line: line.account_id == self.profit)
        self.assertTrue(fx_lines)
        self.assertEqual(fx_lines[0].name, "Cambio")
