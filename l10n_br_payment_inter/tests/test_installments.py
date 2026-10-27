# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
from contextlib import contextmanager
from itertools import count
from unittest import SkipTest
from unittest.mock import patch

from odoo.tests import tagged

from .common import PDF_CONTENT, BancoInterCommon

_MIXIN = "odoo.addons.l10n_br_payment_inter.models.banco_inter_mixin" ".BancoInterMixin"


@tagged("post_install", "-at_install")
class TestBoletoInterInstallments(BancoInterCommon):
    """Um boleto por parcela, e cada boleto paga a sua parcela."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.company
        if not company.chart_template_id:
            raise SkipTest("A empresa do teste precisa de um plano de contas.")

        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Cliente Parcelado",
                "legal_name": "Cliente Parcelado LTDA",
                "is_company": True,
                "cnpj_cpf": "98.016.373/0001-55",
                "street": "Rua das Flores",
                "street_number": "100",
                "district": "Centro",
                "zip": "37540-000",
                "state_id": cls.env.ref("base.state_br_mg").id,
                "city": "Santa Rita do Sapucai",
            }
        )
        cls.bank_journal = cls.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", company.id)], limit=1
        )
        cls.method_line = cls.bank_journal.inbound_payment_method_line_ids[:1]
        cls.payment_mode = cls.env["account.payment.mode"].create(
            {
                "name": "Boleto Inter (parcelas)",
                "company_id": company.id,
                "payment_method_id": cls.env.ref(
                    "account.account_payment_method_manual_in"
                ).id,
                "bank_account_link": "fixed",
                "fixed_journal_id": cls.bank_journal.id,
                "payment_provider_id": cls.provider.id,
            }
        )
        payment_term = cls.env["account.payment.term"].create(
            {
                "name": "30/60",
                "line_ids": [
                    (0, 0, {"value": "percent", "value_amount": 50.0, "days": 30}),
                    (0, 0, {"value": "balance", "value_amount": 0.0, "days": 60}),
                ],
            }
        )
        cls.invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.partner.id,
                "invoice_date": "2026-01-05",
                "invoice_payment_term_id": payment_term.id,
                "payment_mode_id": cls.payment_mode.id,
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

    @contextmanager
    def _patch_bank(self):
        """Banco que registra cada boleto com um codigo de solicitacao novo."""
        numbers = count(1)
        pdf = base64.b64encode(PDF_CONTENT)
        with patch(
            f"{_MIXIN}.add_boleto_inter",
            side_effect=lambda *a, **k: {"codigoSolicitacao": f"cod-{next(numbers)}"},
        ) as add_boleto, patch(f"{_MIXIN}.download_boleto_pdf_inter", return_value=pdf):
            yield add_boleto

    def _generate(self):
        with self._patch_bank() as add_boleto:
            self.invoice.generate_boletos()
        return add_boleto

    def _boleto_txs(self):
        return self.invoice.transaction_ids.filtered(
            lambda t: t.provider_code == "inter"
        )

    def _pay(self, tx):
        tx._set_done()
        return tx._create_payment(payment_method_line_id=self.method_line.id)

    def test_one_boleto_per_installment(self):
        """Cada transacao aponta para a sua parcela, com valor e vencimento dela."""
        add_boleto = self._generate()

        txs = self._boleto_txs()
        self.assertEqual(add_boleto.call_count, 2)
        self.assertEqual(len(txs), 2)
        self.assertEqual(txs.move_line_id, self.first | self.second)
        for tx in txs:
            self.assertEqual(tx.amount, tx.move_line_id.amount_residual)
            self.assertEqual(tx.due_date, tx.move_line_id.date_maturity)
            self.assertEqual(tx.state, "pending")

    def test_generating_again_does_not_duplicate(self):
        self._generate()
        add_boleto = self._generate()

        self.assertEqual(add_boleto.call_count, 0)
        self.assertEqual(len(self._boleto_txs()), 2)

    def test_out_of_order_payment_settles_its_own_installment(self):
        """O boleto da segunda parcela, pago primeiro, nao abate a primeira."""
        self._generate()
        second_tx = self._boleto_txs().filtered(
            lambda t: t.due_date == self.second.date_maturity
        )

        self._pay(second_tx)

        self.assertTrue(self.second.reconciled)
        self.assertFalse(self.first.reconciled)
        self.assertEqual(self.first.amount_residual, 100.0)
        self.assertEqual(self.invoice.amount_residual, 100.0)

    def test_canceled_boleto_is_generated_again_with_the_same_index(self):
        """Parcela com boleto cancelado ganha boleto novo, com o indice dela.

        O indice e a posicao da parcela na fatura: pagar a primeira parcela nao
        muda o numero do boleto da segunda.
        """
        self._generate()
        first_tx, second_tx = self._boleto_txs().sorted("due_date")
        self._pay(first_tx)
        second_tx._set_canceled()

        add_boleto = self._generate()

        self.assertEqual(add_boleto.call_count, 1)
        retry = self._boleto_txs().filtered(
            lambda t: t.move_line_id == self.second and t.state == "pending"
        )
        self.assertEqual(len(retry), 1)
        self.assertNotEqual(retry.reference, second_tx.reference)
        self.assertTrue(retry.our_number.endswith("/2"))
        self.assertEqual(retry.our_number, second_tx.our_number)
