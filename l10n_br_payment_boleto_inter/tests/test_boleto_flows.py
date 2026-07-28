# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

from odoo.exceptions import UserError, ValidationError
from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger
from odoo.tools.misc import hmac as hmac_tool

from .common import PDF_CONTENT, BancoInterCommon, ResponseStub

_TX_LOGGER = "odoo.addons.l10n_br_payment_boleto_inter.models.payment_transaction"


@tagged("post_install", "-at_install")
class TestBoletoInterFlows(BancoInterCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Cliente Boleto",
                "legal_name": "Cliente Boleto LTDA",
                "is_company": True,
                "cnpj_cpf": "11.222.333/0001-81",
                "street": "Rua das Flores",
                "street_number": "100",
                "district": "Centro",
                "zip": "37540-000",
                "state_id": cls.env.ref("base.state_br_mg").id,
                "city": "Santa Rita do Sapucaí",
                "email": "cliente@example.com",
            }
        )
        cls.currency = cls.env.ref("base.BRL")
        journal = cls.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", cls.env.company.id)], limit=1
        )
        method = cls.env["account.payment.method"].search(
            [("code", "=", "manual"), ("payment_type", "=", "inbound")], limit=1
        )
        cls.payment_mode = cls.env["account.payment.mode"].create(
            {
                "name": "Boleto Inter (TEST)",
                "company_id": cls.env.company.id,
                "payment_method_id": method.id,
                "bank_account_link": "fixed",
                "fixed_journal_id": journal.id,
                "payment_provider_id": cls.provider.id,
                "payment_boleto_penalty": 2.0,
                "payment_boleto_interest": 1.0,
                "payment_boleto_discount": 5.0,
                "payment_boleto_discount_days": 3,
            }
        )
        cls.invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.partner.id,
                "payment_mode_id": cls.payment_mode.id,
                "invoice_date_due": "2026-09-10",
            }
        )

    def _create_transaction(self, **values):
        return self.env["payment.transaction"].create(
            {
                "provider_id": self.provider.id,
                "reference": values.pop("reference", "BOL-0001"),
                "amount": values.pop("amount", 150.0),
                "currency_id": self.currency.id,
                "partner_id": self.partner.id,
                "is_boleto_payment": True,
                "due_date": values.pop("due_date", "2026-09-10"),
                **values,
            }
        )

    def _created_boleto_responses(self):
        pdf_base64 = base64.b64encode(PDF_CONTENT).decode()
        return [
            self.token_response,
            ResponseStub(
                status_code=201,
                json_data={"codigoSolicitacao": self.codigo_solicitacao},
            ),
            self.token_response,
            ResponseStub(json_data={"pdf": pdf_base64}),
        ]

    def test_boleto_payload(self):
        """O payload leva pagador, vencimento e valor da transação."""
        tx = self._create_transaction()
        with self._patch_session(self._created_boleto_responses()) as session:
            tx.generate_boleto()

        payload = session.calls[1]["json"]
        self.assertEqual(payload["seuNumero"], "BOL-0001")
        self.assertEqual(payload["valorNominal"], 150.0)
        self.assertEqual(payload["dataVencimento"], "2026-09-10")
        self.assertEqual(payload["pagador"]["cpfCnpj"], "11222333000181")
        self.assertEqual(payload["pagador"]["tipoPessoa"], "JURIDICA")
        self.assertEqual(payload["pagador"]["cep"], "37540000")

    def test_boleto_is_registered_and_pending(self):
        """A transação guarda o código de solicitação e fica pendente."""
        tx = self._create_transaction()
        with self._patch_session(self._created_boleto_responses()):
            tx.generate_boleto()

        self.assertEqual(tx.codigo_solicitacao, self.codigo_solicitacao)
        self.assertEqual(tx.state, "pending")
        self.assertEqual(base64.b64decode(tx.boleto_pdf), PDF_CONTENT)

    @mute_logger(_TX_LOGGER)
    def test_boleto_without_codigo_solicitacao(self):
        """Uma resposta sem código de solicitação é erro."""
        tx = self._create_transaction()
        with self._patch_session(
            [self.token_response, ResponseStub(status_code=201, json_data={})]
        ):
            with self.assertRaises(UserError):
                tx.generate_boleto()

    def test_boleto_of_a_partner_without_address(self):
        """Faltando dado obrigatório do pagador, nada é enviado ao banco."""
        self.partner.street_number = False
        tx = self._create_transaction()
        with self.assertRaises(ValidationError):
            tx._prepare_boleto_data_inter()

    def test_charges_come_from_the_payment_mode(self):
        """Desconto, multa e juros saem do modo de pagamento da fatura."""
        tx = self._create_transaction(invoice_ids=[(6, 0, self.invoice.ids)])
        payload = tx._prepare_boleto_data_inter()

        self.assertEqual(payload["desconto"]["taxa"], 5.0)
        self.assertEqual(payload["desconto"]["quantidadeDias"], 3)
        self.assertEqual(payload["multa"]["taxa"], 200.0)
        self.assertEqual(payload["mora"]["taxa"], 100.0)

    def test_no_charges_without_a_payment_mode(self):
        """Sem modo de pagamento, o boleto vai sem desconto, multa nem juros."""
        tx = self._create_transaction()
        payload = tx._prepare_boleto_data_inter()

        self.assertNotIn("desconto", payload)
        self.assertNotIn("multa", payload)
        self.assertNotIn("mora", payload)

    @mute_logger(_TX_LOGGER)
    def test_cancel_transaction(self):
        """O cancelamento no banco cancela a transação no Odoo."""
        tx = self._create_transaction()
        with self._patch_session(self._created_boleto_responses()):
            tx.generate_boleto()

        with self._patch_session([self.token_response, ResponseStub(status_code=204)]):
            tx.action_cancel_transaction()

        self.assertEqual(tx.state, "cancel")

    def test_cancel_without_codigo_solicitacao(self):
        tx = self._create_transaction()
        with self.assertRaises(UserError):
            tx.action_cancel_transaction()

    def test_cron_marks_the_boleto_as_paid(self):
        """O cron confirma a transação quando o boleto é recebido."""
        tx = self._create_transaction()
        with self._patch_session(self._created_boleto_responses()):
            tx.generate_boleto()

        self._clear_token_cache()
        with self._patch_session(
            [
                self.token_response,
                ResponseStub(json_data={"cobranca": {"situacao": "RECEBIDO"}}),
            ]
        ):
            self.env["payment.transaction"].cron_update_boleto_status()

        self.assertEqual(tx.state, "done")

    def test_cron_cancels_an_expired_boleto(self):
        tx = self._create_transaction(reference="BOL-0002")
        with self._patch_session(self._created_boleto_responses()):
            tx.generate_boleto()

        self._clear_token_cache()
        with self._patch_session(
            [
                self.token_response,
                ResponseStub(json_data={"cobranca": {"situacao": "VENCIDO"}}),
            ]
        ):
            self.env["payment.transaction"].cron_update_boleto_status()

        self.assertEqual(tx.state, "cancel")

    @mute_logger(_TX_LOGGER)
    def test_cron_survives_a_failing_request(self):
        """Um boleto que não pode ser consultado não derruba o cron."""
        tx = self._create_transaction(reference="BOL-0003")
        with self._patch_session(self._created_boleto_responses()):
            tx.generate_boleto()

        self._clear_token_cache()
        with self._patch_session([self.token_response, ResponseStub(status_code=500)]):
            self.env["payment.transaction"].cron_update_boleto_status()

        self.assertEqual(tx.state, "pending")


@tagged("post_install", "-at_install")
class TestBoletoInterAccess(BancoInterCommon, HttpCase):
    """O boleto traz dados pessoais do pagador: a rota precisa ser protegida."""

    def setUp(self):
        super().setUp()
        self.tx = self.env["payment.transaction"].create(
            {
                "provider_id": self.provider.id,
                "reference": "BOL-ACCESS",
                "amount": 10.0,
                "currency_id": self.env.ref("base.BRL").id,
                "partner_id": self.env.ref("base.res_partner_2").id,
                "boleto_pdf": base64.b64encode(PDF_CONTENT),
            }
        )
        self.url = f"/payment/boleto/{self.tx.id}"

    def _access_token(self):
        token_str = "|".join([self.tx.reference, str(self.tx.partner_id.id)])
        return hmac_tool(self.env(su=True), "generate_access_token", token_str)

    @mute_logger("odoo.http")
    def test_public_visitor_without_token_is_rejected(self):
        """Sem token, um visitante não baixa o boleto de outra pessoa."""
        response = self.url_open(self.url)
        self.assertNotIn(b"%PDF", response.content)

    def test_access_token_grants_access(self):
        """Com o token da transação, o pagador baixa o boleto."""
        response = self.url_open(f"{self.url}?access_token={self._access_token()}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, PDF_CONTENT)

    @mute_logger("odoo.http")
    def test_tampered_token_is_rejected(self):
        response = self.url_open(f"{self.url}?access_token=tampered")
        self.assertNotIn(b"%PDF", response.content)

    def test_internal_user_does_not_need_a_token(self):
        """O time interno abre o boleto pelo backend."""
        self.authenticate("admin", "admin")
        response = self.url_open(self.url)
        self.assertEqual(response.content, PDF_CONTENT)
