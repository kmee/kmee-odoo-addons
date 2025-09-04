import base64
import json
import logging
import tempfile
from datetime import datetime, timedelta

from requests import Session

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

SCOPE = {
    "cobranca_add": "boleto-cobranca.write",
    "cobranca_cancel": "boleto-cobranca.write",
    "cobranca_get": "boleto-cobranca.read",
    "extrato.read": "extrato.read",
}


class BancoInterMixin(models.AbstractModel):
    _name = "banco.inter.mixin"
    _description = "Banco Inter Operations"

    def _inter_get_api_url(self, provider_id):
        """
        Retorna a URL base da API do Banco Inter
        com base no estado do provider.
        """
        if provider_id.state == "test":
            return "https://cdpj-sandbox.partners.uatinter.co/"
        elif provider_id.state == "enabled":
            return "https://cdpj.partners.bancointer.com.br/"
        return ""

    def _generate_cert_files(self, provider_id):
        cert = base64.b64decode(provider_id.inter_certificate)
        key = (
            base64.b64decode(provider_id.inter_private_key)
            if provider_id.inter_private_key
            else None
        )
        cert_path = tempfile.mkstemp()[1]
        with open(cert_path, "wb") as f:
            f.write(cert)

        if key:
            key_path = tempfile.mkstemp()[1]
            with open(key_path, "wb") as f:
                f.write(key)
            return (cert_path, key_path)
        return cert_path

    def _prepare_session_request(self, provider_id):
        session = Session()
        session.verify = True
        session.cert = self._generate_cert_files(provider_id)
        return session

    def _generate_header(self, token, provider_id):
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "x-conta-corrente": provider_id.inter_conta_corrente,
        }

    def _check_existing_token(self):
        IrParamSudo = self.env["ir.config_parameter"].sudo()
        expiration = IrParamSudo.get_param("bancointer.token.expiration")
        if not expiration:
            return False
        expiration = datetime.fromisoformat(expiration)
        if expiration < datetime.now():
            return False
        token = IrParamSudo.get_param("bancointer.token")
        return token

    def _save_token(self, token):
        IrParamSudo = self.env["ir.config_parameter"].sudo()
        IrParamSudo.set_param("bancointer.token", token)
        expiration = datetime.now() + timedelta(hours=1)
        IrParamSudo.set_param("bancointer.token.expiration", expiration.isoformat())

    def _get_token(self, provider_id, scope):
        token = self._check_existing_token()
        if token:
            return token

        base_url = self._inter_get_api_url(provider_id)
        url = base_url + "oauth/v2/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        body = {
            "client_id": provider_id.inter_client_id,
            "client_secret": provider_id.inter_client_secret,
            "scope": SCOPE[scope],
            "grant_type": "client_credentials",
        }

        session = self._prepare_session_request(provider_id)
        response = session.post(url, headers=headers, data=body, timeout=30)

        try:
            response.raise_for_status()
            token = response.json().get("access_token")
            if not token:
                raise UserError(_("Token não encontrado na resposta da API"))
            self._save_token(token)
            return token
        except Exception as e:
            _logger.error("Erro ao obter token: %s", str(e))
            raise UserError(_(f"Erro ao obter token de acesso: {str(e)}")) from e

    def add_boleto_inter(self, provider_id, vals):
        """Cria boleto na API V3"""
        token = self._get_token(provider_id, "cobranca_add")
        base_url = self._inter_get_api_url(provider_id)
        url = base_url + "cobranca/v3/cobrancas"
        headers = self._generate_header(token, provider_id)
        session = self._prepare_session_request(provider_id)

        try:
            _logger.info("Enviando requisição para: %s", url)
            _logger.info("Payload: %s", json.dumps(vals, indent=2))
            response = session.post(url, headers=headers, json=vals, timeout=30)
            _logger.info("Resposta HTTP: %s", response.status_code)
            _logger.info("Resposta texto: %s", response.text)

            if response.status_code in [200, 201]:
                return response.json()
            elif response.status_code == 400:
                raise UserError(_(f"Erro nos dados enviados: {response.text}"))
            elif response.status_code == 401:
                raise UserError(
                    _("Erro de autorização ao acessar a API do Banco Inter")
                )
            else:
                raise UserError(
                    _(
                        f"Erro da API do Banco Inter "
                        f"({response.status_code}): {response.text}"
                    )
                )
        except Exception as e:
            _logger.error("Erro ao criar boleto: %s", str(e), exc_info=True)
            raise UserError(_(f"Erro ao criar boleto: {str(e)}")) from e

    def get_boleto_inter_pdf(self, provider_id, codigo_solicitacao):
        """Baixa PDF do boleto usando V3"""
        token = self._get_token(provider_id, "cobranca_get")
        base_url = self._inter_get_api_url(provider_id)
        url = base_url + f"cobranca/v3/cobrancas/{codigo_solicitacao}/pdf"
        headers = self._generate_header(token, provider_id)
        session = self._prepare_session_request(provider_id)

        try:
            response = session.get(url, headers=headers, timeout=30)
            if response.status_code != 200:
                _logger.warning(
                    "Erro ao baixar PDF do boleto %s: %s",
                    codigo_solicitacao,
                    response.text,
                )
                return ""
            return base64.b64encode(response.content).decode("utf-8")
        except Exception as e:
            _logger.error(
                "Erro ao baixar PDF do boleto %s: %s", codigo_solicitacao, str(e)
            )
            return ""

    def get_boleto_status_inter(self, provider_id, codigo_solicitacao):
        """
        Consulta o status de um boleto na API V3 do Banco Inter
        Retorna o JSON com a cobrança e informações relevantes.
        """
        token = self._get_token_force_new(provider_id, "cobranca_get")
        base_url = self._inter_get_api_url(provider_id)
        url = f"{base_url}cobranca/v3/cobrancas/{codigo_solicitacao}"
        headers = {
            "Authorization": f"Bearer {token}",
            "x-conta-corrente": provider_id.inter_conta_corrente,
            "Content-Type": "application/json",
        }
        session = self._prepare_session_request(provider_id)

        try:
            _logger.info("Consultando status do boleto: %s", codigo_solicitacao)
            response = session.get(url, headers=headers, timeout=30)
            _logger.info("Status HTTP: %s", response.status_code)
            _logger.info("Resposta: %s", response.text)

            if response.status_code == 200:
                data = response.json()
                situacao = data.get("cobranca", {}).get("situacao")
                _logger.info(
                    "Boleto %s situação atual: %s", codigo_solicitacao, situacao
                )
                return data
            elif response.status_code == 404:
                raise UserError(
                    _(
                        f"Boleto não encontrado para codigoSolicitacao {codigo_solicitacao}"
                    )
                )
            elif response.status_code == 401:
                raise UserError(
                    _("Erro de autorização ao consultar boleto no Banco Inter")
                )
            else:
                raise UserError(
                    _(
                        f"Erro ao consultar boleto ({response.status_code}): {response.text}"
                    )
                )
        except Exception as e:
            _logger.error("Erro ao consultar boleto: %s", str(e), exc_info=True)
            raise UserError(_(f"Erro ao consultar boleto: {str(e)}")) from e

    def cancel_boleto_inter(self, provider_id, codigo_solicitacao):
        """Cancela boleto usando V3"""
        token = self._get_token(provider_id, "cobranca_cancel")
        base_url = self._inter_get_api_url(provider_id)
        url = base_url + f"cobranca/v3/cobrancas/{codigo_solicitacao}/cancelar"
        headers = self._generate_header(token, provider_id)
        session = self._prepare_session_request(provider_id)
        vals = {"motivoCancelamento": "SUBSTITUICAO"}

        try:
            response = session.post(url, headers=headers, json=vals, timeout=30)
            if response.status_code not in [200, 204]:
                raise UserError(_(f"Erro ao cancelar boleto: {response.text}"))
            return True
        except Exception as e:
            _logger.error("Erro ao cancelar boleto %s: %s", codigo_solicitacao, str(e))
            raise UserError(_(f"Erro ao cancelar boleto: {str(e)}")) from e

    def download_boleto_pdf_inter(self, provider, codigo_solicitacao):
        """
        Baixa PDF do boleto Inter usando token específico para leitura.
        Trata resposta JSON que contém o PDF em base64.
        """
        # Força novo token com escopo correto para leitura
        token = self._get_token_force_new(provider, "cobranca_get")
        base_url = self._inter_get_api_url(provider)
        pdf_url = f"{base_url}cobranca/v3/cobrancas/{codigo_solicitacao}/pdf"
        headers = {
            "Authorization": f"Bearer {token}",
            "x-conta-corrente": provider.inter_conta_corrente,
            "Content-Type": "application/json",
        }
        session = self._prepare_session_request(provider)

        try:
            _logger.info("Baixando PDF do boleto: %s", pdf_url)
            response = session.get(pdf_url, headers=headers, timeout=30)
            _logger.info("Status da resposta PDF: %s", response.status_code)
            _logger.info(
                "Tamanho do conteúdo: %s bytes",
                len(response.content) if response.content else 0,
            )

            if response.status_code != 200:
                _logger.error("Erro HTTP %s: %s", response.status_code, response.text)
                raise UserError(
                    f"Erro ao baixar boleto PDF: {response.status_code} - {response.text}"
                )

            # Tenta decodificar a resposta como JSON
            try:
                response_json = response.json()
                _logger.info("Resposta é um JSON")

                # Verifica se tem a chave 'pdf'
                if "pdf" in response_json:
                    pdf_base64 = response_json["pdf"]
                    _logger.info(
                        "PDF extraído do JSON. Tamanho: %s caracteres", len(pdf_base64)
                    )

                    # Valida se é realmente um PDF (decodifica e verifica header)
                    try:
                        pdf_content = base64.b64decode(pdf_base64)
                        if not pdf_content.startswith(b"%PDF"):
                            _logger.warning(
                                "Conteúdo decodificado não parece ser um PDF válido"
                            )
                            _logger.debug("Primeiros 20 bytes: %s", pdf_content[:20])
                        else:
                            _logger.info("PDF válido confirmado")

                        return pdf_base64

                    except Exception as decode_error:
                        _logger.error(
                            "Erro ao decodificar base64: %s", str(decode_error)
                        )
                        raise UserError(
                            _("PDF retornado está corrompido")
                        ) from decode_error
                else:
                    _logger.error(
                        "JSON não contém chave 'pdf': %s", list(response_json.keys())
                    )
                    raise UserError(_("Resposta da API não contém PDF"))

            except ValueError:
                # Se não conseguir decodificar como JSON, tenta como binário
                _logger.info("Resposta não é JSON, tratando como binário")

                if response.content.startswith(b"%PDF"):
                    # É um PDF direto
                    pdf_base64 = base64.b64encode(response.content).decode("utf-8")
                    _logger.info(
                        "PDF binário convertido para base64. Tamanho: %s caracteres",
                        len(pdf_base64),
                    )
                    return pdf_base64
                else:
                    _logger.error("Conteúdo não é PDF nem JSON válido")
                    _logger.debug("Primeiros 100 bytes: %s", response.content[:100])

        except Exception as e:
            _logger.exception("Falha ao baixar PDF do boleto")
            raise UserError(_("Erro ao baixar PDF do boleto")) from e

    def _get_token_force_new(self, provider_id, scope):
        """Força a geração de um novo token, ignorando cache"""
        _logger.info("Forçando novo token para escopo: %s", scope)
        base_url = self._inter_get_api_url(provider_id)
        url = base_url + "oauth/v2/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        body = {
            "client_id": provider_id.inter_client_id,
            "client_secret": provider_id.inter_client_secret,
            "scope": SCOPE[scope],
            "grant_type": "client_credentials",
        }

        session = self._prepare_session_request(provider_id)
        response = session.post(url, headers=headers, data=body, timeout=30)

        try:
            response.raise_for_status()
            token_data = response.json()
            token = token_data.get("access_token")
            if not token:
                raise UserError(_("Token não encontrado na resposta da API"))
            _logger.info("Novo token gerado com sucesso para escopo: %s", scope)
            return token
        except Exception as e:
            _logger.error("Erro ao obter token forçado: %s", str(e))
            raise UserError(_(f"Erro ao obter token de acesso: {str(e)}")) from e
