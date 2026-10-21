# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import PDF_CONTENT, BancoInterCommon

GENERATE = (
    "odoo.addons.l10n_br_payment_boleto_inter.models.payment_transaction."
    "PaymentTransaction.generate_boleto"
)


@tagged("post_install", "-at_install")
class TestInvoiceBoletos(BancoInterCommon):
    """A fatura emite um boleto Inter por parcela em aberto."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Cliente Parcelado"})
        journal = cls.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", cls.env.company.id)], limit=1
        )
        method = cls.env["account.payment.method"].search(
            [("code", "=", "manual"), ("payment_type", "=", "inbound")], limit=1
        )
        cls.payment_mode = cls.env["account.payment.mode"].create(
            {
                "name": "Boleto Inter (parcelas)",
                "company_id": cls.env.company.id,
                "payment_method_id": method.id,
                "bank_account_link": "fixed",
                "fixed_journal_id": journal.id,
                "payment_provider_id": cls.provider.id,
                "payment_boleto_penalty": 2.0,
                "payment_boleto_interest": 1.0,
                "payment_boleto_instructions": "Nao receber apos 30 dias",
            }
        )
        cls.payment_term = cls.env["account.payment.term"].create(
            {
                "name": "30/60",
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
        cls.invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.partner.id,
                "payment_mode_id": cls.payment_mode.id,
                "invoice_payment_term_id": cls.payment_term.id,
                "invoice_date": "2026-09-01",
                "currency_id": cls.env.company.currency_id.id,
                "invoice_line_ids": [
                    (0, 0, {"name": "Servico", "quantity": 1, "price_unit": 200.0})
                ],
            }
        )
        cls.invoice.action_post()

    def test_one_boleto_per_open_installment(self):
        with patch(GENERATE) as generate:
            self.invoice.generate_boletos()
        txs = self.invoice.transaction_ids
        self.assertEqual(len(txs), 2)
        self.assertEqual(generate.call_count, 2)
        self.assertEqual(
            sorted(txs.mapped("amount")), [100.0, 100.0], "one boleto per installment"
        )
        self.assertEqual(
            sorted(txs.mapped("due_date")),
            sorted(self.invoice.due_line_ids.mapped("date_maturity")),
        )
        tx = txs[0]
        self.assertTrue(tx.is_boleto_payment)
        self.assertEqual(tx.boleto_penalty, 2.0)
        self.assertEqual(tx.boleto_interest, 1.0)
        self.assertEqual(tx.boleto_instructions, "Nao receber apos 30 dias")
        self.assertTrue(tx.our_number.endswith(("/1", "/2")))

    def test_generating_again_does_not_duplicate(self):
        """Boleto vivo no banco não é emitido de novo para o mesmo vencimento."""
        with patch(GENERATE):
            self.invoice.generate_boletos()
        self.invoice.transaction_ids.write(
            {"codigo_solicitacao": "abc", "state": "pending"}
        )
        with patch(GENERATE) as generate:
            self.invoice.generate_boletos()
        self.assertEqual(generate.call_count, 0)
        self.assertEqual(len(self.invoice.transaction_ids), 2)

    def test_without_provider(self):
        self.payment_mode.payment_provider_id = False
        with self.assertRaises(UserError):
            self.invoice._create_boletos_inter()
        with self.assertRaises(UserError):
            self.invoice._prepare_boleto_payload(self.invoice.due_line_ids[:1], 1)

    def test_transactions_with_pdf_are_listed_by_due_date(self):
        with patch(GENERATE):
            self.invoice.generate_boletos()
        txs = self.invoice.transaction_ids
        self.assertFalse(self.invoice._get_boleto_inter_transactions())
        txs.write({"boleto_pdf": base64.b64encode(PDF_CONTENT)})
        listed = self.invoice._get_boleto_inter_transactions()
        self.assertEqual(listed, txs.sorted("due_date"))

    def test_sale_order_transactions(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        self.assertFalse(order._get_boleto_inter_transactions())
        with patch(GENERATE):
            self.invoice.generate_boletos()
        txs = self.invoice.transaction_ids
        txs.write(
            {
                "boleto_pdf": base64.b64encode(PDF_CONTENT),
                "sale_order_ids": [(6, 0, order.ids)],
            }
        )
        self.assertEqual(order._get_boleto_inter_transactions(), txs.sorted("due_date"))
