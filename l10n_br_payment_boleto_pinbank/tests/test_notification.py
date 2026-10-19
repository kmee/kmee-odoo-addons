from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from .common import PinbankCommon, boleto_response, patch_make_request


@tagged("post_install", "-at_install")
class TestPinbankNotification(PinbankCommon):
    """O PinBank identifica o boleto pelo nosso numero, nunca pela referencia."""

    def setUp(self):
        super().setUp()
        self.tx = self._create_tx(our_number="123456789", state="authorized")

    def test_notification_finds_the_transaction_by_our_number(self):
        tx = self.env["payment.transaction"]._get_tx_from_notification_data(
            "boleto_pinbank", boleto_response("123456789", "LIQUIDADO")
        )

        self.assertEqual(tx, self.tx)

    def test_notification_is_processed_on_the_transaction(self):
        self.env["payment.transaction"]._handle_notification_data(
            "boleto_pinbank", boleto_response("123456789", "LIQUIDADO")
        )

        self.assertEqual(self.tx.state, "done")

    def test_notification_with_status_only(self):
        """Resposta sem linha digitavel atualiza o estado sem KeyError."""
        self.tx.write({"digitable_line": "linha", "barcode": "barras"})

        self.env["payment.transaction"]._handle_notification_data(
            "boleto_pinbank",
            {"Data": {"NossoNumero": "123456789", "Status": "LIQUIDADO"}},
        )

        self.assertEqual(self.tx.state, "done")
        self.assertEqual(self.tx.digitable_line, "linha")
        self.assertEqual(self.tx.barcode, "barras")

    def test_unknown_our_number_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.env["payment.transaction"]._get_tx_from_notification_data(
                "boleto_pinbank", boleto_response("999999999", "LIQUIDADO")
            )

    def test_refund_request_sends_our_number(self):
        """A baixa vai com o nosso numero e o resultado cai na transacao de estorno."""
        self.tx._set_done()

        with patch_make_request(
            return_value=boleto_response("123456789", "BAIXA")
        ) as make_request:
            refund_tx = self.tx._send_refund_request()

        payload = make_request.call_args.kwargs["payload"]
        self.assertEqual(payload["Data"]["NossoNumero"], "123456789")
        self.assertEqual(payload["Data"]["CodigoCanal"], 10)
        self.assertEqual(payload["Data"]["CodigoCliente"], 1000)
        self.assertEqual(refund_tx.source_transaction_id, self.tx)
        self.assertNotEqual(refund_tx.state, "draft")
        self.assertEqual(self.tx.state, "done", "a baixa nao cancela o boleto pago")

    def test_refund_notification_without_our_number(self):
        """Estorno sem nosso numero e erro de dado, nao KeyError."""
        with self.assertRaises(ValidationError):
            self.env["payment.transaction"]._get_tx_from_notification_data(
                "boleto_pinbank", {"entity_type": "refund", "Data": {}}
            )

    def test_refund_initiated_by_the_bank(self):
        """Estorno vindo do banco cria a transacao de estorno do boleto de origem."""
        notification = boleto_response("123456789", "BAIXA")
        notification["entity_type"] = "refund"

        refund_tx = self.env["payment.transaction"]._get_tx_from_notification_data(
            "boleto_pinbank", notification
        )

        self.assertEqual(refund_tx.source_transaction_id, self.tx)
        self.assertEqual(refund_tx.operation, "refund")
