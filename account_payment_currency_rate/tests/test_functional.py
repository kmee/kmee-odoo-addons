# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPaymentCurrencyRate(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Rate Partner"})
        cls.product = cls.env["product.product"].create({"name": "Rate Product"})
        cls.invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.partner.id,
                "invoice_date": "2026-01-10",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "quantity": 1,
                            "price_unit": 100.0,
                        },
                    )
                ],
            }
        )
        cls.invoice.action_post()

    def _wizard(self):
        ctx = {
            "active_model": "account.move",
            "active_ids": self.invoice.ids,
        }
        return Form(self.env["account.payment.register"].with_context(**ctx))

    def test_change_rate_percent(self):
        form = self._wizard()
        wizard = form.save()
        self.assertTrue(wizard.original_rate)
        wizard.change_rate = wizard.original_rate * 2
        wizard.onchange_change_rate()
        self.assertAlmostEqual(wizard.change_rate_percent, 2.0, places=5)

    def test_onchange_currency_sets_change_rate(self):
        wizard = self._wizard().save()
        wizard.change_rate = 5
        wizard.onchange_currency_id()
        self.assertEqual(wizard.change_rate, wizard.original_rate)
