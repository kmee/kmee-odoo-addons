# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPurchasePaymentTermManual(TransactionCase):
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
        cls.vendor = cls.env["res.partner"].create({"name": "Vendor"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Product",
                "type": "service",
                "purchase_method": "purchase",
                "standard_price": 1000.0,
            }
        )

    def _purchase_order(self):
        order = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "payment_term_id": self.term.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_qty": 1,
                            "price_unit": 1000.0,
                            "taxes_id": False,
                        },
                    )
                ],
            }
        )
        order._update_manual_payment_term_id(self.term)
        return order

    def _installments(self, invoice):
        lines = invoice.line_ids.filtered(lambda x: x.display_type == "payment_term")
        return sorted((x.date_maturity, abs(x.balance)) for x in lines)

    def test_manual_term_is_copied_from_the_payment_term(self):
        order = self._purchase_order()
        self.assertEqual(order.manual_payment_term_id.origin_term_id, self.term)
        self.assertEqual(len(order.manual_payment_term_line_ids), 2)
        self.assertFalse(order.has_manual_lines)

    def test_invoice_copies_the_manual_term(self):
        order = self._purchase_order()
        manual = order.manual_payment_term_id
        manual.line_ids.filtered(lambda x: x.value == "percent").write(
            {"value_amount": 30.0, "fixed_date": date(2024, 2, 20)}
        )
        manual.line_ids.filtered(lambda x: x.value == "balance").write(
            {"fixed_date": date(2024, 4, 10)}
        )
        order.button_confirm()
        order.action_create_invoice()
        invoice = order.invoice_ids
        self.assertEqual(len(invoice), 1)
        # the invoice has its own copy: the order can change without touching it
        self.assertTrue(invoice.manual_payment_term_id)
        self.assertNotEqual(invoice.manual_payment_term_id, manual)
        self.assertTrue(invoice.has_manual_lines)
        self.assertEqual(
            self._installments(invoice),
            [(date(2024, 2, 20), 300.0), (date(2024, 4, 10), 700.0)],
        )

    def test_invoice_without_manual_edit_uses_the_payment_term(self):
        order = self._purchase_order()
        order.button_confirm()
        order.action_create_invoice()
        invoice = order.invoice_ids
        invoice.invoice_date = date(2024, 1, 15)
        invoice.recompute_payment_lines()
        self.assertEqual(
            self._installments(invoice),
            [(date(2024, 2, 14), 500.0), (date(2024, 3, 15), 500.0)],
        )

    def test_order_without_manual_term(self):
        order = self._purchase_order()
        order.manual_payment_term_id = False
        order.button_confirm()
        order.action_create_invoice()
        self.assertFalse(order.invoice_ids.manual_payment_term_id)
