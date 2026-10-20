from odoo.tests.common import HttpCase, tagged

from .common import PinbankCommon, boleto_response, patch_make_request


@tagged("post_install", "-at_install")
class TestPinbankRenderingValues(PinbankCommon):
    def test_rendering_values_of_other_providers(self):
        """O override nao pode quebrar o checkout dos outros providers."""
        other_provider = self.env["payment.provider"].create(
            {"name": "Outro provider", "code": "none"}
        )
        tx = self._create_tx(reference="OUTRO-1", provider_id=other_provider.id)

        self.assertEqual(tx._get_specific_rendering_values({}), {})

    def test_rendering_values_use_the_our_number(self):
        tx = self._create_tx(our_number="123456789")

        values = tx._get_specific_rendering_values({})

        self.assertEqual(values["order_id"], "123456789")
        self.assertIn("/payment/pinbank/return?reference=", values["return_url"])


@tagged("post_install", "-at_install")
class TestPinbankReturn(HttpCase):
    """O retorno reconsulta o banco e nunca confia no que chega na URL."""

    def setUp(self):
        super().setUp()
        provider = self.env.ref(
            "l10n_br_payment_boleto_pinbank.payment_acquirer_boleto_pinbank"
        )
        provider.write(
            {
                "pinbank_user": "abcd1234",
                "pinbank_secret": "secret",
                "pinbank_channel": 10,
                "pinbank_client": 1000,
                "pinbank_request_origin": "1",
                "state": "test",
            }
        )
        partner = self.env["res.partner"].create({"name": "Cliente Retorno"})
        self.tx = self.env["payment.transaction"].create(
            {
                "reference": "RETORNO/1",
                "amount": 100.0,
                "currency_id": self.env.ref("base.BRL").id,
                "partner_id": partner.id,
                "provider_id": provider.id,
                "is_boleto_payment": True,
                "our_number": "123456789",
                "state": "pending",
            }
        )

    def test_return_checks_the_status_in_the_bank(self):
        with patch_make_request(
            return_value=boleto_response("123456789", "LIQUIDADO")
        ) as make_request:
            response = self.url_open("/payment/pinbank/return?reference=RETORNO/1")

        self.assertEqual(response.status_code, 200)
        make_request.assert_called_once()
        self.assertEqual(self.tx.state, "done")

    def test_return_ignores_the_posted_status(self):
        with patch_make_request(
            return_value=boleto_response("123456789", "REGISTRADO")
        ):
            self.url_open(
                "/payment/pinbank/return?reference=RETORNO/1&Status=LIQUIDADO"
            )

        self.assertEqual(self.tx.state, "authorized")

    def test_return_with_unknown_reference(self):
        with patch_make_request() as make_request:
            response = self.url_open("/payment/pinbank/return?reference=NAO-EXISTE")

        self.assertEqual(response.status_code, 200)
        make_request.assert_not_called()
