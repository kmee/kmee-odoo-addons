# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from odoo import Command
from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestMisPurchaseCommitmentDue(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Due = cls.env["mis.purchase.commitment.due"]
        cls.vendor = cls.env["res.partner"].create({"name": "Vendor"})
        cls.product = cls.env["product.product"].create(
            {"name": "Item", "type": "consu", "supplier_taxes_id": [Command.clear()]}
        )
        cls.term_30 = cls.env.ref("account.account_payment_term_30days")
        cls.term_split = cls.env["account.payment.term"].create(
            {
                "name": "30/60",
                "line_ids": [
                    Command.create(
                        {"value": "percent", "value_amount": 50.0, "nb_days": 30}
                    ),
                    Command.create(
                        {"value": "percent", "value_amount": 50.0, "nb_days": 60}
                    ),
                ],
            }
        )
        cls.planned = datetime(2026, 12, 1, 12, 0)

    def _order(self, term, qty=10.0, price=100.0):
        return self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "payment_term_id": term.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_qty": qty,
                            "price_unit": price,
                            "date_planned": self.planned,
                            "taxes_id": [Command.clear()],
                        }
                    )
                ],
            }
        )

    def _lines(self, order):
        return self.Due.search([("purchase_order_id", "=", order.id)], order="date")

    def test_01_draft_not_committed(self):
        order = self._order(self.term_30)
        self.assertFalse(self._lines(order))

    def test_02_confirmed_single_installment(self):
        order = self._order(self.term_30)
        order.button_confirm()
        lines = self._lines(order)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines.date, (self.planned + timedelta(days=30)).date())
        self.assertEqual(lines.credit, 1000.0)
        self.assertEqual(lines.amount, 1000.0)
        self.assertEqual(lines.account_id, self.vendor.property_account_payable_id)

    def test_03_split_terms(self):
        order = self._order(self.term_split)
        order.button_confirm()
        lines = self._lines(order)
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines.mapped("credit"), [500.0, 500.0])
        self.assertEqual(
            lines.mapped("date"),
            [
                (self.planned + timedelta(days=30)).date(),
                (self.planned + timedelta(days=60)).date(),
            ],
        )

    def test_04_partial_invoice_reduces_commitment(self):
        order = self._order(self.term_30)
        order.button_confirm()
        move_form = Form(
            self.env["account.move"].with_context(default_move_type="in_invoice")
        )
        move_form.partner_id = self.vendor
        move_form.invoice_date = self.planned.date()
        move_form.purchase_vendor_bill_id = self.env["purchase.bill.union"].browse(
            -order.id
        )
        invoice = move_form.save()
        invoice.invoice_line_ids.quantity = 4.0
        invoice.action_post()
        lines = self._lines(order)
        self.assertEqual(sum(lines.mapped("amount")), 600.0)
        invoice.button_draft()
        self.assertEqual(sum(self._lines(order).mapped("amount")), 1000.0)

    def test_05_cancel_removes_commitment(self):
        order = self._order(self.term_30)
        order.button_confirm()
        order.button_cancel()
        self.assertFalse(self._lines(order))

    def test_06_cron_resync(self):
        order = self._order(self.term_30)
        order.button_confirm()
        self._lines(order).unlink()
        self.Due._cron_sync_all()
        self.assertEqual(len(self._lines(order)), 1)

    def test_07_mis_move_lines_source_compatible(self):
        model = self.env["ir.model"].search(
            [("model", "=", "mis.purchase.commitment.due")]
        )
        report = self.env["mis.report"].create(
            {"name": "Commitments", "move_lines_source": model.id}
        )
        self.assertEqual(report.account_model, "account.account")
