# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date
from decimal import Decimal

from brbank import StatusCanonico, TipoInstrucao

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import FAKE_BASIC, BrbankTransactionCase


@tagged("post_install", "-at_install")
class TestBrbankTransaction(BrbankTransactionCase):
    def _standalone_tx(self):
        tx = self.env["payment.transaction"].create(
            {
                "reference": self.env["payment.transaction"]._compute_reference(
                    "brbank", prefix="TESTE"
                ),
                "provider_id": self.provider.id,
                "partner_id": self.partner.id,
                "amount": 50.0,
                "currency_id": self.env.ref("base.BRL").id,
                "operation": "offline",
                "is_boleto_payment": True,
                "due_date": date(2026, 2, 1),
            }
        )
        tx._brbank_register()
        return tx

    def test_state_map(self):
        """O2: each canonical status lands in its transaction state."""
        expected = {
            StatusCanonico.PENDENTE_REGISTRO: "pending",
            StatusCanonico.REGISTRADO: "authorized",
            StatusCanonico.BAIXADO: "cancel",
            StatusCanonico.REJEITADO: "error",
        }
        for status, state in expected.items():
            with self.subTest(status=status):
                tx = self._standalone_tx()
                tx.state = "draft"
                tx._brbank_apply_status(status)
                self.assertEqual(tx.state, state)

    def test_state_map_settled(self):
        """O2: LIQUIDADO -> done, with the payment of the installment."""
        invoice = self._create_invoice()
        tx = self._brbank_txs(invoice)[0]
        tx._brbank_apply_status(StatusCanonico.LIQUIDADO)
        self.assertEqual(tx.state, "done")
        self.assertTrue(tx.payment_id)
        self.assertTrue(tx.is_post_processed)

    def test_done_never_goes_back(self):
        """A settled transaction ignores a later write-off status."""
        invoice = self._create_invoice()
        tx = self._brbank_txs(invoice)[0]
        tx._brbank_apply_status(StatusCanonico.LIQUIDADO)
        payment = tx.payment_id
        tx._brbank_apply_status(StatusCanonico.BAIXADO)
        self.assertEqual(tx.state, "done")
        self.assertEqual(payment.state, "posted")

    def test_capture_reads_the_bank(self):
        """`payment` capture on a boleto queries the bank (base semantics)."""
        tx = self._standalone_tx()
        self._set_bank_status(tx, StatusCanonico.LIQUIDADO, Decimal("50.00"))
        tx.action_capture()
        self.assertEqual(tx.state, "done")

    def test_instruction_supported(self):
        """O6: a due date extension accepted by the bank."""
        tx = self._standalone_tx()
        instruction = self.env["l10n_br.boleto.instruction"].create(
            {
                "transaction_id": tx.id,
                "command": "prorrogacao",
                "new_due_date": date(2026, 3, 1),
            }
        )
        self.assertTrue(instruction.action_send())
        self.assertEqual(instruction.state, "done")
        self.assertTrue(instruction.idempotency_key)
        self.assertEqual(tx.due_date, date(2026, 3, 1))
        self.assertEqual(self._bank_title(tx)["vencimento"], date(2026, 3, 1))
        self.assertIn(("instrucao", "PRORROGACAO"), self.bank["calls"])

    def test_instruction_not_supported_by_the_bank(self):
        """O6: NaoSuportado of the adapter rejects the instruction."""
        tx = self._standalone_tx()
        self.bank["unsupported"] = {TipoInstrucao.NEGATIVACAO}
        instruction = self.env["l10n_br.boleto.instruction"].create(
            {"transaction_id": tx.id, "command": "negativacao"}
        )
        action = instruction.action_send()
        self.assertEqual(action["tag"], "display_notification")
        self.assertEqual(instruction.state, "rejected")
        self.assertIn("not supported", instruction.result_message)
        self.assertEqual(tx.state, "authorized")

    def test_instruction_capability_missing(self):
        """O11: a bank without ALTERACAO refuses before calling the bank."""
        provider = self._create_provider(FAKE_BASIC)
        self.assertFalse(provider.brbank_supports_instruction)
        self.assertTrue(provider.brbank_supports_write_off)
        tx = self._standalone_tx()
        tx.provider_id = provider
        instruction = self.env["l10n_br.boleto.instruction"].create(
            {"transaction_id": tx.id, "command": "protesto"}
        )
        with self.assertRaises(UserError):
            instruction.action_send()
        self.assertNotIn(("instrucao", "PROTESTO"), self.bank["calls"])

    def test_write_off(self):
        tx = self._standalone_tx()
        tx.action_brbank_write_off()
        self.assertEqual(tx.state, "cancel")
        self.assertEqual(tx.brbank_bank_status, "BAIXADO")

    def test_pdf_downloaded_when_the_bank_provides_it(self):
        tx = self._standalone_tx()
        self.assertTrue(tx.boleto_pdf)
        action = tx.action_brbank_download_pdf()
        self.assertIn(f"/web/content/payment.transaction/{tx.id}/", action["url"])

    def test_reconcile_cron(self):
        """O8: the cron reads back the open titles of every brbank provider."""
        invoice = self._create_invoice()
        txs = self._brbank_txs(invoice)
        self._set_bank_status(txs[0], StatusCanonico.LIQUIDADO, Decimal("300.00"))
        self._set_bank_status(txs[1], StatusCanonico.BAIXADO)
        self.bank["calls"].clear()
        self.env.ref(
            "l10n_br_payment_brbank.ir_cron_brbank_reconcile"
        ).method_direct_trigger()
        self.assertEqual(txs.mapped("state"), ["done", "cancel", "authorized"])
        consulted = {call[1] for call in self.bank["calls"] if call[0] == "consultar"}
        self.assertTrue(set(txs.mapped("provider_reference")) <= consulted)

    def test_report_shows_the_titles(self):
        """O5: digitable line and Pix copy and paste on the invoice."""
        invoice = self._create_invoice()
        html = (
            self.env["ir.actions.report"]
            ._render_qweb_html("account.account_invoices", invoice.ids)[0]
            .decode()
        )
        for tx in self._brbank_txs(invoice):
            self.assertIn(tx.digitable_line, html)
            self.assertIn(tx.pix_copia_cola, html)

    def test_cnab_bridge(self):
        """O10: a return file occurrence reads the title back by nosso numero."""
        tx = self._standalone_tx()
        self._set_bank_status(tx, StatusCanonico.LIQUIDADO, Decimal("50.00"))
        found = self.env["payment.transaction"]._brbank_notify_cnab_occurrence(
            tx.our_number
        )
        self.assertEqual(found, tx)
        self.assertEqual(tx.state, "done")
