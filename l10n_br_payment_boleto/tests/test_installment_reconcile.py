# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest import SkipTest

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBoletoInstallmentReconcile(TransactionCase):
    """Cada boleto paga a sua parcela, mesmo quando o cliente paga fora de ordem."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        company = cls.env.company
        if not company.chart_template_id:
            raise SkipTest("A empresa do teste precisa de um plano de contas.")

        cls.bank_journal = cls.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", company.id)], limit=1
        )
        cls.method_line = cls.bank_journal.inbound_payment_method_line_ids[:1]
        cls.provider = cls.env["payment.provider"].create(
            {
                "name": "Boleto (teste de parcela)",
                "code": "none",
                "state": "test",
                "company_id": company.id,
            }
        )
        cls.payment_term = cls.env["account.payment.term"].create(
            {
                "name": "30/60",
                "line_ids": [
                    (0, 0, {"value": "percent", "value_amount": 50.0, "days": 30}),
                    (0, 0, {"value": "balance", "value_amount": 0.0, "days": 60}),
                ],
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Cliente Parcelado"})
        cls.invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.partner.id,
                "invoice_date": "2026-01-05",
                "invoice_payment_term_id": cls.payment_term.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Servico",
                            "quantity": 1,
                            "price_unit": 200.0,
                            "tax_ids": [(6, 0, [])],
                        },
                    )
                ],
            }
        )
        cls.invoice.action_post()
        cls.first, cls.second = cls.invoice.due_line_ids.sorted("date_maturity")

    def _pay_installment(self, installment, **extra_vals):
        tx = self.env["payment.transaction"].create(
            {
                "reference": f"boleto-{installment.id}",
                "provider_id": self.provider.id,
                "amount": installment.amount_residual,
                "currency_id": self.invoice.currency_id.id,
                "partner_id": self.partner.id,
                "is_boleto_payment": True,
                "due_date": installment.date_maturity,
                "invoice_ids": [(6, 0, self.invoice.ids)],
                **extra_vals,
            }
        )
        tx._set_done()
        tx._create_payment(payment_method_line_id=self.method_line.id)
        return tx

    def test_out_of_order_payment_settles_its_own_installment(self):
        """O boleto da segunda parcela, pago primeiro, nao abate a primeira."""
        self._pay_installment(self.second, move_line_id=self.second.id)

        self.assertTrue(self.second.reconciled)
        self.assertFalse(self.first.reconciled)
        self.assertEqual(self.first.amount_residual, 100.0)
        self.assertEqual(self.invoice.amount_residual, 100.0)

    def test_installment_paid_with_interest_keeps_the_rest_open(self):
        """Juros pagos a mais nao descem para a parcela seguinte."""
        tx = self.env["payment.transaction"].create(
            {
                "reference": "boleto-com-juros",
                "provider_id": self.provider.id,
                "amount": 103.0,
                "currency_id": self.invoice.currency_id.id,
                "partner_id": self.partner.id,
                "is_boleto_payment": True,
                "due_date": self.first.date_maturity,
                "invoice_ids": [(6, 0, self.invoice.ids)],
                "move_line_id": self.first.id,
            }
        )
        tx._set_done()
        payment = tx._create_payment(payment_method_line_id=self.method_line.id)

        self.assertTrue(self.first.reconciled)
        self.assertEqual(self.second.amount_residual, 100.0)
        counterpart = payment.line_ids.filtered(
            lambda line: line.account_id == payment.destination_account_id
        )
        self.assertEqual(counterpart.amount_residual, -3.0)

    def test_transaction_without_installment_keeps_core_behaviour(self):
        """Sem parcela informada, vale a conciliacao do core."""
        self._pay_installment(self.first)

        self.assertTrue(self.first.reconciled)
        self.assertFalse(self.second.reconciled)

    def test_active_boleto_of_an_installment(self):
        """A checagem de idempotencia olha so a parcela e os estados vivos."""
        self.assertFalse(self.invoice._boleto_get_active_transactions(self.first))
        tx = self.env["payment.transaction"].create(
            {
                "reference": "boleto-ativo",
                "provider_id": self.provider.id,
                "amount": self.first.amount_residual,
                "currency_id": self.invoice.currency_id.id,
                "partner_id": self.partner.id,
                "invoice_ids": [(6, 0, self.invoice.ids)],
                "move_line_id": self.first.id,
            }
        )
        self.assertEqual(self.invoice._boleto_get_active_transactions(self.first), tx)
        self.assertFalse(self.invoice._boleto_get_active_transactions(self.second))

        tx._set_error("recusado")
        self.assertFalse(self.invoice._boleto_get_active_transactions(self.first))
