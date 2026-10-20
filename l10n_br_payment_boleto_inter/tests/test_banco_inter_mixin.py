# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import os

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import PDF_CONTENT, BancoInterCommon, ResponseStub

_MIXIN_LOGGER = "odoo.addons.l10n_br_payment_boleto_inter.models.banco_inter_mixin"


@tagged("post_install", "-at_install")
class TestBancoInterCertificates(BancoInterCommon):
    def test_certificate_files_are_written_and_removed(self):
        """A chave privada não pode sobrar no disco depois da requisição."""
        with self.mixin._inter_certificate_files(self.provider) as cert:
            paths = list(cert)
            self.assertEqual(len(paths), 2)
            for path in paths:
                self.assertTrue(os.path.exists(path))
                self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
            with open(paths[0], "rb") as cert_file:
                self.assertEqual(cert_file.read(), b"certificate")

        self.assertFalse(any(os.path.exists(path) for path in paths))

    def test_certificate_files_are_removed_on_error(self):
        """Uma falha no meio da requisição também limpa os arquivos."""
        paths = []
        with self.assertRaises(ValueError):
            with self.mixin._inter_certificate_files(self.provider) as cert:
                paths = list(cert)
                raise ValueError("boom")
        self.assertTrue(paths)
        self.assertFalse(any(os.path.exists(path) for path in paths))

    def test_certificate_is_required(self):
        """Sem certificado não há requisição ao Inter."""
        self.provider.inter_certificate = False
        with self.assertRaises(UserError):
            with self.mixin._inter_certificate_files(self.provider):
                pass

    def test_single_file_when_there_is_no_private_key(self):
        """Certificado com chave embutida é entregue como caminho único."""
        self.provider.inter_private_key = False
        with self.mixin._inter_certificate_files(self.provider) as cert:
            self.assertIsInstance(cert, str)
            self.assertTrue(os.path.exists(cert))


@tagged("post_install", "-at_install")
class TestBancoInterToken(BancoInterCommon):
    def setUp(self):
        super().setUp()
        self._clear_token_cache()

    def test_token_is_requested_with_the_scope(self):
        """O escopo pedido vai no corpo da requisição do token."""
        with self._patch_session([self.token_response]) as session:
            token = self.mixin._get_token(self.provider, "cobranca_add")

        self.assertEqual(token, "tok-123")
        self.assertEqual(session.calls[0]["data"]["scope"], "boleto-cobranca.write")

    def test_token_is_cached_by_scope(self):
        """O token de escrita não pode ser reusado numa leitura."""
        with self._patch_session([self.token_response]):
            self.mixin._get_token(self.provider, "cobranca_add")
        with self._patch_session([self.token_response]) as session:
            self.mixin._get_token(self.provider, "cobranca_add")
        self.assertEqual(
            session.calls, [], "o token do mesmo escopo foi pedido de novo"
        )

        read_response = ResponseStub(
            json_data={"access_token": "tok-read", "expires_in": 3600}
        )
        with self._patch_session([read_response]) as session:
            token = self.mixin._get_token(self.provider, "cobranca_get")
        self.assertEqual(token, "tok-read")
        self.assertEqual(session.calls[0]["data"]["scope"], "boleto-cobranca.read")

    def test_token_is_cached_by_provider(self):
        """Duas contas Inter não compartilham o mesmo token."""
        other_provider = self.provider.copy({"name": "Outra conta Inter"})
        with self._patch_session([self.token_response]):
            self.mixin._get_token(self.provider, "cobranca_add")

        other_response = ResponseStub(
            json_data={"access_token": "tok-outra", "expires_in": 3600}
        )
        with self._patch_session([other_response]) as session:
            token = self.mixin._get_token(other_provider, "cobranca_add")

        self.assertEqual(token, "tok-outra")
        self.assertTrue(session.calls)

    def test_expired_token_is_renewed(self):
        """Um token vencido é pedido de novo."""
        short_lived = ResponseStub(
            json_data={"access_token": "tok-curto", "expires_in": 1}
        )
        with self._patch_session([short_lived]):
            self.mixin._get_token(self.provider, "cobranca_add")

        params = self.env["ir.config_parameter"].sudo()
        key, expiration_key = self.mixin._inter_token_param_names(
            self.provider, "cobranca_add"
        )
        params.set_param(expiration_key, "2020-01-01T00:00:00")

        with self._patch_session([self.token_response]) as session:
            token = self.mixin._get_token(self.provider, "cobranca_add")

        self.assertEqual(token, "tok-123")
        self.assertTrue(session.calls)

    def test_force_new_token_ignores_the_cache(self):
        with self._patch_session([self.token_response]):
            self.mixin._get_token(self.provider, "cobranca_add")
        with self._patch_session([self.token_response]) as session:
            self.mixin._get_token(self.provider, "cobranca_add", force_new=True)
        self.assertTrue(session.calls)

    @mute_logger(_MIXIN_LOGGER)
    def test_missing_token_in_the_response(self):
        with self._patch_session([ResponseStub(json_data={})]):
            with self.assertRaises(UserError):
                self.mixin._get_token(self.provider, "cobranca_add")


@tagged("post_install", "-at_install")
class TestBancoInterRequests(BancoInterCommon):
    def setUp(self):
        super().setUp()
        self._clear_token_cache()

    def test_add_boleto(self):
        """A cobrança é criada no endpoint v3 e a resposta é devolvida."""
        created = ResponseStub(
            status_code=201, json_data={"codigoSolicitacao": self.codigo_solicitacao}
        )
        with self._patch_session([self.token_response, created]) as session:
            res = self.mixin.add_boleto_inter(self.provider, {"seuNumero": "1"})

        self.assertEqual(res["codigoSolicitacao"], self.codigo_solicitacao)
        self.assertTrue(session.calls[1]["url"].endswith("cobranca/v3/cobrancas"))
        self.assertEqual(session.calls[1]["headers"]["x-conta-corrente"], "123456")

    @mute_logger(_MIXIN_LOGGER)
    def test_add_boleto_with_invalid_data(self):
        """Um 400 do Inter vira mensagem para o usuário."""
        rejected = ResponseStub(status_code=400, content=b"campo invalido")
        with self._patch_session([self.token_response, rejected]):
            with self.assertRaises(UserError):
                self.mixin.add_boleto_inter(self.provider, {})

    def test_status_query(self):
        situacao = ResponseStub(json_data={"cobranca": {"situacao": "RECEBIDO"}})
        with self._patch_session([self.token_response, situacao]):
            data = self.mixin.get_boleto_status_inter(
                self.provider, self.codigo_solicitacao
            )
        self.assertEqual(data["cobranca"]["situacao"], "RECEBIDO")

    @mute_logger(_MIXIN_LOGGER)
    def test_status_query_of_an_unknown_boleto(self):
        with self._patch_session([self.token_response, ResponseStub(status_code=404)]):
            with self.assertRaises(UserError):
                self.mixin.get_boleto_status_inter(self.provider, "no-such-code")

    def test_cancel_boleto(self):
        with self._patch_session(
            [self.token_response, ResponseStub(status_code=204)]
        ) as session:
            self.assertTrue(
                self.mixin.cancel_boleto_inter(self.provider, self.codigo_solicitacao)
            )
        self.assertTrue(session.calls[1]["url"].endswith("/cancelar"))
        self.assertEqual(session.calls[1]["json"]["motivoCancelamento"], "SUBSTITUICAO")

    def test_download_pdf_from_json(self):
        """A API devolve o PDF em base64 dentro de um JSON."""
        pdf_base64 = base64.b64encode(PDF_CONTENT).decode()
        with self._patch_session(
            [self.token_response, ResponseStub(json_data={"pdf": pdf_base64})]
        ):
            res = self.mixin.download_boleto_pdf_inter(
                self.provider, self.codigo_solicitacao
            )
        self.assertEqual(res, pdf_base64)

    def test_download_pdf_from_binary(self):
        """A API também responde com o binário do PDF."""
        with self._patch_session(
            [self.token_response, ResponseStub(content=PDF_CONTENT)]
        ):
            res = self.mixin.download_boleto_pdf_inter(
                self.provider, self.codigo_solicitacao
            )
        self.assertEqual(base64.b64decode(res), PDF_CONTENT)

    @mute_logger(_MIXIN_LOGGER)
    def test_download_pdf_without_pdf(self):
        with self._patch_session(
            [self.token_response, ResponseStub(json_data={"erro": "nao tem"})]
        ):
            with self.assertRaises(UserError):
                self.mixin.download_boleto_pdf_inter(
                    self.provider, self.codigo_solicitacao
                )
