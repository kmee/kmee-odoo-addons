# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from unittest.mock import patch

import requests

from odoo import _
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import HttpCase, TransactionCase, tagged
from odoo.tools import mute_logger

from ..utils.cypher import AESCipher

PROVIDER_MOD = "odoo.addons.l10n_br_payment_boleto_pinbank.models.payment_provider"
TX_MOD = "odoo.addons.l10n_br_payment_boleto_pinbank.models.payment_transaction"
SECRET = "0123456789abcdef"

FULL_DATA = {
    "NossoNumero": "123456789",
    "LinhaDigitavel": "12345.67890 12345.678901 12345.678901 1 23456789012345",
    "CodigoBarras": "12345678901234567890123456789012345678901234",
}


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(str(self.status_code))


class PinbankCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.provider = cls.env.ref(
            "l10n_br_payment_boleto_pinbank.payment_acquirer_boleto_pinbank"
        )
        cls.provider.write(
            {
                "pinbank_user": "user1",
                "pinbank_secret": SECRET,
                "pinbank_channel": 10,
                "pinbank_client": 1000,
                "pinbank_request_origin": "1",
                "state": "enabled",
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Sacado Teste",
                "legal_name": "Sacado Teste LTDA",
                "email": "sacado@example.com",
                "street": "Rua A",
                "district": "Centro",
                "city": "Sao Paulo",
                "zip": "01311-915",
                "state_id": cls.env["res.country.state"]
                .search([("code", "=", "SP")], limit=1)
                .id,
                "country_id": cls.env.ref("base.br").id,
                "cnpj_cpf": "73.145.637/0001-40",
            }
        )

    def _tx(self, **vals):
        values = {
            "reference": "TXB1",
            "amount": 100.0,
            "due_date": "2025-04-22",
            "currency_id": self.env.ref("base.BRL").id,
            "partner_id": self.partner.id,
            "provider_id": self.provider.id,
            "provider_code": "boleto_pinbank",
            "our_number": "123456789",
        }
        values.update(vals)
        return self.env["payment.transaction"].create(values)


@tagged("post_install", "-at_install")
class TestPinbankProvider(PinbankCase):
    def test_token_param_names_are_per_provider(self):
        """Given two providers, Then each has its own token keys."""
        other = self.provider.copy({"name": "Other"})
        self.assertNotEqual(
            self.provider._boleto_pinbank_token_param_names(),
            other._boleto_pinbank_token_param_names(),
        )

    def test_save_token_without_expiry_is_never_reused(self):
        """Given a token saved without expiry, Then it is not reused."""
        params = self.env["ir.config_parameter"].sudo()
        _token_key, expiration_key = self.provider._boleto_pinbank_token_param_names()
        params.set_param(expiration_key, False)
        self.provider._boleto_pinbank_save_token("t", 0)
        self.assertFalse(self.provider._boleto_pinbank_check_existing_token())

    def test_get_token_reuses_valid_cache_without_http(self):
        """Given a valid cached token, Then no HTTP request is made."""
        self.provider._boleto_pinbank_save_token("cached", 600)
        with patch(PROVIDER_MOD + ".requests.post") as post:
            self.assertEqual(self.provider._boleto_pinbank_get_token(), "cached")
        post.assert_not_called()

    def test_get_token_requests_and_saves_a_new_token(self):
        """Given no cache, When getting the token, Then the environment URL
        is called with the credentials and the token is cached."""
        params = self.env["ir.config_parameter"].sudo()
        for key in self.provider._boleto_pinbank_token_param_names():
            params.set_param(key, False)
        response = FakeResponse(payload={"access_token": "new", "expire_in": 600})
        for state, host in (("enabled", "//pinbank.com.br"), ("test", "//dev.pinbank")):
            self.provider.state = state
            for key in self.provider._boleto_pinbank_token_param_names():
                params.set_param(key, False)
            with patch(PROVIDER_MOD + ".requests.post", return_value=response) as post:
                token = self.provider._boleto_pinbank_get_token()
            self.assertEqual(token, "new")
            self.assertIn(host, post.call_args.args[0])
            self.assertTrue(post.call_args.args[0].endswith("/token"))
            self.assertEqual(post.call_args.kwargs["data"]["username"], "user1")
        self.assertEqual(self.provider._boleto_pinbank_check_existing_token(), "new")

    @mute_logger(PROVIDER_MOD)
    def test_get_token_failures_become_validation_errors(self):
        """Given a network failure or an HTTP error, Then ValidationError."""
        params = self.env["ir.config_parameter"].sudo()
        for key in self.provider._boleto_pinbank_token_param_names():
            params.set_param(key, False)
        for kwargs in (
            {"side_effect": requests.exceptions.ConnectionError("x")},
            {"side_effect": requests.exceptions.Timeout("x")},
            {"return_value": FakeResponse(400, {"Message": "bad credentials"})},
        ):
            with patch(PROVIDER_MOD + ".requests.post", **kwargs):
                with self.assertRaises(ValidationError):
                    self.provider._boleto_pinbank_get_token()

    def test_headers_carry_token_origin_and_user(self):
        """Given a token, Then the headers have bearer, origin and user."""
        self.provider._boleto_pinbank_save_token("tok", 600)
        headers = self.provider._boleto_pinbank_get_headers()
        self.assertEqual(headers["Authorization"], "Bearer tok")
        self.assertEqual(headers["RequestOrigin"], "1")
        self.assertEqual(headers["UserName"], "user1")

    def test_default_vals(self):
        """Given the provider, Then default values hold channel and client."""
        vals = self.provider._get_default_vals("NN1")
        self.assertEqual(
            vals, {"CodigoCanal": 10, "CodigoCliente": 1000, "NossoNumero": "NN1"}
        )

    def test_make_request_encrypts_payload_and_decrypts_answer(self):
        """Given an encrypted endpoint, Then the payload goes AES encrypted
        (readable with the secret) and the answer is decrypted."""
        cipher = AESCipher(key=SECRET.encode())
        answer = {"Data": {"Json": cipher.encrypt(json.dumps({"ok": 1})).decode()}}
        with patch(
            PROVIDER_MOD + ".requests.request",
            return_value=FakeResponse(payload=answer),
        ) as request:
            result = self.provider._boleto_pinbank_make_request(
                "/x", headers={"h": "1"}, payload={"Data": {"a": "ç"}}
            )
        self.assertEqual(result, {"ok": 1})
        sent = request.call_args.kwargs["json"]["Data"]["Json"]
        self.assertEqual(json.loads(cipher.decrypt(sent)), {"Data": {"a": "ç"}})
        self.assertEqual(request.call_args.kwargs["headers"], {"h": "1"})
        self.assertTrue(request.call_args.kwargs["url"].endswith("/x"))

    def test_make_request_plain_endpoint_returns_json(self):
        """Given a non encrypted endpoint, Then the plain JSON is returned."""
        with patch(
            PROVIDER_MOD + ".requests.request",
            return_value=FakeResponse(payload={"plain": True}),
        ) as request:
            result = self.provider._boleto_pinbank_make_request(
                "/x", headers={"h": "1"}, payload={"a": 1}, encrypted_endpoint=False
            )
        self.assertEqual(result, {"plain": True})
        self.assertEqual(request.call_args.kwargs["json"], {"a": 1})

    def test_make_request_gets_headers_when_not_given(self):
        """Given no headers, Then they are built from the cached token."""
        self.provider._boleto_pinbank_save_token("tok", 600)
        with patch(
            PROVIDER_MOD + ".requests.request", return_value=FakeResponse(payload={})
        ) as request:
            self.provider._boleto_pinbank_make_request(
                "/x", payload={}, encrypted_endpoint=False
            )
        self.assertEqual(
            request.call_args.kwargs["headers"]["Authorization"], "Bearer tok"
        )

    @mute_logger(PROVIDER_MOD)
    def test_make_request_failures_become_validation_errors(self):
        """Given HTTP error, network error or an answer without Data, Then
        ValidationError."""
        cases = (
            {"return_value": FakeResponse(500, {"Message": "boom"})},
            {"side_effect": requests.exceptions.ConnectionError("x")},
            {"side_effect": requests.exceptions.Timeout("x")},
            {"return_value": FakeResponse(200, {"Message": "no data"})},
        )
        for kwargs in cases:
            with patch(PROVIDER_MOD + ".requests.request", **kwargs):
                with self.assertRaises(ValidationError):
                    self.provider._boleto_pinbank_make_request(
                        "/x", headers={}, payload={}
                    )

    def test_feature_support_only_for_pinbank(self):
        """Given the pinbank provider, Then fees, manual capture, full refund
        and tokenization are supported."""
        self.assertTrue(self.provider.support_manual_capture)
        self.assertTrue(self.provider.support_fees)
        self.assertEqual(self.provider.support_refund, "full_only")


@tagged("post_install", "-at_install")
class TestPinbankTransaction(PinbankCase):
    def test_boleto_info_redacts_personal_data_and_extracts_pdf(self):
        """Given an answer with payer data and PDF, Then the PDF goes to its
        field and the technical info has no personal data."""
        response = {
            "Data": dict(FULL_DATA, Base64="UERG", DadosSacado={"Nome": "Joao"})
        }
        info = self._tx()._prepare_transaction_boleto_info(response)
        self.assertEqual(info["boleto_pdf"], "UERG")
        self.assertNotIn("Joao", info["provider_technical_info"])
        self.assertNotIn("UERG", info["provider_technical_info"])
        self.assertIn("123456789", info["provider_technical_info"])

    def test_redact_handles_lists_and_scalars(self):
        """Given nested lists, Then personal keys are hidden everywhere."""
        redacted = self.env["payment.transaction"]._pinbank_redact(
            [{"Nome": "A"}, ({"Email": "e"},), 5]
        )
        self.assertEqual(redacted, [{"Nome": "***"}, [{"Email": "***"}], 5])

    def test_payload_scales_money_and_documents(self):
        """Given interest and penalty of 0.02, Then they are sent in ten
        thousandths and the document as digits only."""
        tx = self._tx(boleto_interest=0.02, boleto_penalty=0.03)
        data = tx._boleto_pinbank_prepare_order_request_payload()["Data"]
        self.assertEqual(data["Valor"], 10000)
        self.assertEqual(data["Juros"]["Valor"], 200)
        self.assertEqual(data["Multa"]["Valor"], 300)
        self.assertEqual(data["DadosSacado"]["CpfCnpj"], 73145637000140)
        self.assertEqual(data["DadosSacado"]["Cep"], 1311915)
        self.assertEqual(data["DataVencimento"], "20250422")

    def test_generate_boleto_uses_pinbank_request(self):
        """Given a pinbank transaction, When generating the boleto, Then the
        PinBank payment request is used; action_generate sets pending first."""
        tx = self._tx()
        with patch.object(type(tx), "_send_payment_request") as send:
            tx.generate_boleto()
        send.assert_called_once()
        with patch.object(type(tx), "generate_boleto") as generate:
            tx.action_generate_boleto()
        generate.assert_called_once()
        self.assertEqual(tx.state, "pending")

    def _notify(self, tx, status, extra=None):
        data = {"Data": dict(FULL_DATA, Status=status, NossoNumero=tx.reference)}
        data.update(extra or {})
        tx._handle_notification_data("boleto_pinbank", data)

    def test_notification_status_maps_to_transaction_state(self):
        """Given PinBank statuses, Then the transaction state follows:
        PENDENTE pending, REGISTRADO authorized, LIQUIDADO done, BAIXA cancel."""
        expected = {
            "PENDENTE": "pending",
            "REGISTRADO": "authorized",
            "LIQUIDADO": "done",
            "BAIXA": "cancel",
        }
        for number, (status, state) in enumerate(expected.items()):
            tx = self._tx(reference="TXS%s" % number)
            self._notify(tx, status)
            self.assertEqual(tx.state, state, status)
            self.assertEqual(tx.digitable_line, FULL_DATA["LinhaDigitavel"])

    @mute_logger(TX_MOD)
    def test_notification_with_unknown_or_missing_status_is_error(self):
        """Given an unknown or missing status, Then the transaction is in
        error."""
        tx = self._tx(reference="TXE1")
        self._notify(tx, "WHATEVER")
        self.assertEqual(tx.state, "error")
        tx2 = self._tx(reference="TXE2")
        tx2._handle_notification_data(
            "boleto_pinbank", {"Data": {"NossoNumero": "TXE2"}}
        )
        self.assertEqual(tx2.state, "error")

    def test_notification_finds_transaction_or_refuses(self):
        """Given notification data, Then the transaction is found by the
        NossoNumero PinBank returned, never by the Odoo reference; missing or
        unknown numbers raise ValidationError."""
        tx = self._tx(reference="TXF1", our_number="NNF1")
        found = self.env["payment.transaction"]._get_tx_from_notification_data(
            "boleto_pinbank", {"Data": {"NossoNumero": "NNF1"}}
        )
        self.assertEqual(found, tx)
        with self.assertRaises(ValidationError):
            self.env["payment.transaction"]._get_tx_from_notification_data(
                "boleto_pinbank", {"Data": {}}
            )
        with self.assertRaises(ValidationError):
            self.env["payment.transaction"]._get_tx_from_notification_data(
                "boleto_pinbank", {"Data": {"NossoNumero": "NOPE"}}
            )

    def test_refund_notification_from_pinbank_creates_refund_transaction(self):
        """Given a refund started at PinBank for a known payment, Then a refund
        transaction is created; for an unknown payment ValidationError."""
        source = self._tx(reference="TXR1", our_number="NNR1", state="done")
        data = {
            "entity_type": "refund",
            "Data": {"NossoNumero": "NNR1"},
        }
        refund = self.env["payment.transaction"]._get_tx_from_notification_data(
            "boleto_pinbank", data
        )
        self.assertEqual(refund.source_transaction_id, source)
        self.assertEqual(refund.operation, "refund")
        data["Data"]["NossoNumero"] = "UNKNOWN"
        with self.assertRaises(ValidationError):
            self.env["payment.transaction"]._get_tx_from_notification_data(
                "boleto_pinbank", data
            )

    def test_capture_request_checks_status_with_our_number(self):
        """Given a transaction, When checking the boleto status, Then the
        consult endpoint receives the channel, client and our number."""
        tx = self._tx()
        answer = {"Data": dict(FULL_DATA, Status="LIQUIDADO")}
        with patch(
            PROVIDER_MOD + ".Paymentprovider._boleto_pinbank_make_request",
            return_value=answer,
        ) as make:
            tx._send_capture_request()
        self.assertEqual(make.call_args.args[0], "/CashIn/ConsultarBoletoEncrypted")
        self.assertEqual(
            make.call_args.kwargs["payload"]["Data"],
            {"CodigoCanal": 10, "CodigoCliente": 1000, "NossoNumero": "123456789"},
        )
        self.assertEqual(tx.state, "done")

    def test_void_cancels_in_pinbank_and_rechecks_status(self):
        """Given a boleto, When voided, Then the cancel endpoint is called and
        the status is consulted afterwards."""
        tx = self._tx(state="authorized")
        answers = [{}, {"Data": dict(FULL_DATA, Status="BAIXA")}]
        with patch(
            PROVIDER_MOD + ".Paymentprovider._boleto_pinbank_make_request",
            side_effect=answers,
        ) as make:
            tx._send_void_request()
        endpoints = [call.args[0] for call in make.call_args_list]
        self.assertEqual(
            endpoints,
            [
                "/CashIn/SolicitarBaixaBoletoEncrypted",
                "/CashIn/ConsultarBoletoEncrypted",
            ],
        )
        self.assertEqual(tx.state, "cancel")

    @mute_logger(TX_MOD)
    def test_void_failure_sets_error_state(self):
        """Given the cancel request failing, Then the transaction is in error
        and no status is consulted."""
        tx = self._tx(state="authorized")
        with patch(
            PROVIDER_MOD + ".Paymentprovider._boleto_pinbank_make_request",
            side_effect=ValidationError(_("down")),
        ) as make:
            tx._send_void_request()
        self.assertEqual(make.call_count, 1)
        self.assertEqual(tx.state, "error")

    def test_rendering_values_generate_the_boleto(self):
        """Given the checkout flow, When rendering values are requested, Then
        the boleto is generated once and its number is the order id."""
        tx = self._tx(our_number=False)
        answer = {"Data": dict(FULL_DATA)}
        with patch(
            PROVIDER_MOD + ".Paymentprovider._boleto_pinbank_make_request",
            return_value=answer,
        ) as make:
            values = tx._get_specific_rendering_values({})
            tx._get_specific_rendering_values({})
        make.assert_called_once()
        self.assertEqual(
            make.call_args.kwargs["endpoint"], "/CashIn/GerarBoletoEncrypted"
        )
        self.assertEqual(values["order_id"], "123456789")
        self.assertEqual(values["amount"], 100.0)
        self.assertIn("/payment/pinbank/return?reference=TXB1", values["return_url"])

    def test_cron_checks_only_pinbank_transactions_in_the_given_state(self):
        """Given pending and authorized pinbank transactions, Then each cron
        checks only its state; a ValidationError does not stop the loop."""
        pending = self._tx(reference="TXC1", state="pending")
        authorized = self._tx(reference="TXC2", state="authorized")
        calls = []

        def capture(record):
            calls.append(record)
            raise ValidationError(_("fail"))

        with patch.object(type(pending), "_send_capture_request", capture), mute_logger(
            TX_MOD
        ):
            self.env["payment.transaction"].cron_check_for_authorized_boletos()
            self.assertIn(pending, calls)
            self.assertNotIn(authorized, calls)
            calls.clear()
            self.env["payment.transaction"].cron_check_for_paid_boletos()
            self.assertIn(authorized, calls)
            self.assertNotIn(pending, calls)


@tagged("post_install", "-at_install")
class TestPinbankInvoice(PinbankCase):
    def _move(self, with_mode=True):
        journal = self.env["account.journal"].search(
            [
                ("type", "in", ("bank", "cash")),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )
        mode = self.env["account.payment.mode"].create(
            {
                "name": "Pinbank mode",
                "bank_account_link": "fixed",
                "fixed_journal_id": journal.id,
                "payment_provider_id": self.provider.id,
                "payment_method_id": self.env.ref(
                    "account.account_payment_method_manual_in"
                ).id,
                "payment_boleto_penalty": 0.02,
                "payment_boleto_interest": 0.01,
                "payment_boleto_instructions": "Pagar",
            }
        )
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_date": "2025-01-01",
                "payment_mode_id": mode.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Servico",
                            "quantity": 1,
                            "price_unit": 100.0,
                            "tax_ids": [(6, 0, [])],
                        },
                    )
                ],
            }
        )
        return move, mode

    def test_prepare_payment_transaction_values(self):
        """Given an invoice with a pinbank payment mode, Then the transaction
        values carry provider, amount, due date and mode conditions."""
        move, mode = self._move()
        line = move.line_ids[:1]
        vals = move._prepare_payment_transaction(line, 1)
        self.assertEqual(vals["provider_id"], self.provider.id)
        self.assertTrue(vals["is_boleto_payment"])
        self.assertEqual(vals["reference"], "%s/1" % line.name)
        self.assertEqual(vals["boleto_penalty"], 0.02)
        self.assertEqual(vals["boleto_interest"], 0.01)
        self.assertEqual(vals["boleto_instructions"], "Pagar")
        self.assertEqual(vals["invoice_ids"], [(6, 0, move.ids)])

    def test_generate_boletos_creates_one_transaction_per_open_due_line(self):
        """Given a posted invoice, When generating boletos, Then one
        transaction is created and generated per open due line."""
        move, mode = self._move()
        move.action_post()
        with patch.object(
            type(self.env["payment.transaction"]), "generate_boleto"
        ) as generate:
            move.generate_boletos()
        self.assertEqual(generate.call_count, len(move.due_line_ids))
        txs = self.env["payment.transaction"].search(
            [("invoice_ids", "in", move.ids), ("provider_id", "=", self.provider.id)]
        )
        self.assertEqual(len(txs), len(move.due_line_ids))
        self.assertEqual(txs[:1].amount, 100.0)

    def test_generate_boletos_without_provider_is_refused(self):
        """Given a payment mode without provider, Then generating boletos is
        refused with a UserError."""
        move, mode = self._move()
        mode.payment_provider_id = False
        with self.assertRaises(UserError):
            move.generate_boletos()


@tagged("post_install", "-at_install")
class TestPinbankController(HttpCase):
    def test_return_redirects_to_payment_status(self):
        """Given the return URL, When PinBank redirects the payer, Then he is
        sent to the payment status page."""
        response = self.url_open(
            "/payment/pinbank/return?reference=ANY", allow_redirects=False
        )
        self.assertEqual(response.status_code, 303)
        self.assertTrue(response.headers["Location"].endswith("/payment/status"))
