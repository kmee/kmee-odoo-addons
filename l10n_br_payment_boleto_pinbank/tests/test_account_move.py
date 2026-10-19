from itertools import count
from unittest import SkipTest

from odoo.tests.common import tagged

from .common import PinbankCommon, boleto_response, patch_make_request


@tagged("post_install", "-at_install")
class TestPinbankInvoiceBoletos(PinbankCommon):
    """Um boleto vivo por parcela, nunca dois."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.company
        if not company.chart_template_id:
            raise SkipTest("A empresa do teste precisa de um plano de contas.")

        bank_journal = cls.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", company.id)], limit=1
        )
        cls.payment_mode = cls.env["account.payment.mode"].create(
            {
                "name": "Boleto PinBank",
                "bank_account_link": "fixed",
                "fixed_journal_id": bank_journal.id,
                "payment_method_id": cls.env.ref(
                    "account.account_payment_method_manual_in"
                ).id,
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

    def _generate(self):
        numbers = count(1)
        with patch_make_request(
            side_effect=lambda *a, **k: boleto_response(str(next(numbers)).zfill(9))
        ) as make_request:
            self.invoice.generate_boletos()
        return make_request

    def _boleto_txs(self):
        return self.invoice.transaction_ids.filtered(
            lambda t: t.provider_code == "boleto_pinbank"
        )

    def test_one_boleto_per_installment(self):
        make_request = self._generate()

        txs = self._boleto_txs()
        self.assertEqual(make_request.call_count, 2)
        self.assertEqual(len(txs), 2)
        self.assertEqual(txs.move_line_id, self.first | self.second)
        for tx in txs:
            self.assertEqual(tx.amount, tx.move_line_id.amount_residual)
            self.assertEqual(tx.due_date, tx.move_line_id.date_maturity)

    def test_generating_again_does_not_duplicate(self):
        self._generate()
        make_request = self._generate()

        self.assertEqual(make_request.call_count, 0)
        self.assertEqual(len(self._boleto_txs()), 2)

    def test_failed_boleto_can_be_generated_again(self):
        self._generate()
        failed = self._boleto_txs().filtered(lambda t: t.move_line_id == self.second)
        failed._set_error("recusado pelo banco")

        make_request = self._generate()

        self.assertEqual(make_request.call_count, 1)
        retry = self._boleto_txs().filtered(
            lambda t: t.move_line_id == self.second and t.state != "error"
        )
        self.assertEqual(len(retry), 1)
        self.assertNotEqual(retry.reference, failed.reference)
