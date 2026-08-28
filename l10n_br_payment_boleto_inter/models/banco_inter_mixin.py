import base64
import contextlib
import json
import logging
import os
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

# O token é renovado um pouco antes de expirar, para absorver a ida e volta.
TOKEN_EXPIRATION_MARGIN = 60


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

    @contextlib.contextmanager
    def _inter_certificate_files(self, provider_id):
        """Escreve o certificado e a chave privada em arquivos temporários.

        Os arquivos são criados com permissão restrita e removidos assim que a
        requisição termina: a chave privada não pode ficar no disco.

        :param provider_id: O provider com as credenciais.
        :return: A tupla esperada pelo argumento `cert` do requests.
        :rtype: tuple|str
        """
        provider_sudo = provider_id.sudo()
        if not provider_sudo.inter_certificate:
            raise UserError(
                _("Configure o certificado do Banco Inter no provider de pagamento.")
            )

        contents = [provider_sudo.inter_certificate]
        if provider_sudo.inter_private_key:
            contents.append(provider_sudo.inter_private_key)

        paths = []
        try:
            for content in contents:
                file_descriptor, path = tempfile.mkstemp(suffix=".pem")
                with os.fdopen(file_descriptor, "wb") as pem_file:
                    pem_file.write(base64.b64decode(content))
                os.chmod(path, 0o600)
                paths.append(path)
            yield tuple(paths) if len(paths) > 1 else paths[0]
        finally:
            for path in paths:
                with contextlib.suppress(OSError):
                    os.remove(path)

    @contextlib.contextmanager
    def _inter_session(self, provider_id):
        """Devolve uma sessão configurada com o certificado do Banco Inter.

        :param provider_id: O provider com as credenciais.
        :return: A sessão pronta para uso.
        :rtype: requests.Session
        """
        with self._inter_certificate_files(provider_id) as cert:
            session = Session()
            session.verify = True
            session.cert = cert
            try:
                yield session
            finally:
                session.close()

    def _generate_header(self, token, provider_id):
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "x-conta-corrente": provider_id.inter_conta_corrente,
        }

    def _inter_token_param_names(self, provider_id, scope):
        """Devolve as chaves usadas para guardar o token.

        O token é emitido por escopo e por conta: guardar um único token para
        toda a base faz uma requisição de leitura reusar o token de escrita de
        outro provider.

        :param provider_id: O provider dono do token.
        :param str scope: O escopo pedido.
        :return: As chaves do token e da sua expiração.
        :rtype: tuple
        """
        suffix = f"{provider_id.id}.{scope}"
        return (
            f"bancointer.token.{suffix}",
            f"bancointer.token.expiration.{suffix}",
        )

    def _check_existing_token(self, provider_id, scope):
        IrParamSudo = self.env["ir.config_parameter"].sudo()
        token_key, expiration_key = self._inter_token_param_names(provider_id, scope)
        expiration = IrParamSudo.get_param(expiration_key)
        if not expiration:
            return False
        try:
            expiration = datetime.fromisoformat(expiration)
        except ValueError:
            return False
        if expiration < datetime.now():
            return False
        return IrParamSudo.get_param(token_key)

    def _save_token(self, provider_id, scope, token, expires_in=None):
        IrParamSudo = self.env["ir.config_parameter"].sudo()
        token_key, expiration_key = self._inter_token_param_names(provider_id, scope)
        IrParamSudo.set_param(token_key, token)
        lifetime = max(
            int(expires_in or 3600) - TOKEN_EXPIRATION_MARGIN,
            TOKEN_EXPIRATION_MARGIN,
        )
        expiration = datetime.now() + timedelta(seconds=lifetime)
        IrParamSudo.set_param(expiration_key, expiration.isoformat())

    def _get_token(self, provider_id, scope, force_new=False):
        """Devolve um token válido para o escopo, pedindo um novo se preciso.

        :param provider_id: O provider com as credenciais.
        :param str scope: A chave do escopo em `SCOPE`.
        :param bool force_new: Ignora o token guardado.
        :return: O token de acesso.
        :rtype: str
        """
        if not force_new:
            token = self._check_existing_token(provider_id, scope)
            if token:
                return token

        base_url = self._inter_get_api_url(provider_id)
        url = base_url + "oauth/v2/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        body = {
            "client_id": provider_id.sudo().inter_client_id,
            "client_secret": provider_id.sudo().inter_client_secret,
            "scope": SCOPE[scope],
            "grant_type": "client_credentials",
        }

        try:
            with self._inter_session(provider_id) as session:
                response = session.post(url, headers=headers, data=body, timeout=30)
            response.raise_for_status()
            token_data = response.json()
        except UserError:
            raise
        except Exception as e:
            _logger.error("Erro ao obter token: %s", str(e))
            raise UserError(_("Erro ao obter token de acesso: %s", str(e))) from e

        token = token_data.get("access_token")
        if not token:
            raise UserError(_("Token não encontrado na resposta da API"))
        self._save_token(provider_id, scope, token, token_data.get("expires_in"))
        return token

    def add_boleto_inter(self, provider_id, vals):
        """Cria boleto na API V3"""
        token = self._get_token(provider_id, "cobranca_add")
        base_url = self._inter_get_api_url(provider_id)
        url = base_url + "cobranca/v3/cobrancas"
        headers = self._generate_header(token, provider_id)

        try:
            _logger.info("Enviando requisição para: %s", url)
            _logger.debug("Payload: %s", json.dumps(vals, indent=2))
            with self._inter_session(provider_id) as session:
                response = session.post(url, headers=headers, json=vals, timeout=30)
            _logger.info("Resposta HTTP: %s", response.status_code)
        except UserError:
            raise
        except Exception as e:
            _logger.error("Erro ao criar boleto: %s", str(e), exc_info=True)
            raise UserError(_("Erro ao criar boleto: %s", str(e))) from e

        if response.status_code in [200, 201]:
            return response.json()
        elif response.status_code == 400:
            raise UserError(_("Erro nos dados enviados: %s", response.text))
        elif response.status_code == 401:
            raise UserError(_("Erro de autorização ao acessar a API do Banco Inter"))
        raise UserError(
            _(
                "Erro da API do Banco Inter (%(status)s): %(body)s",
                status=response.status_code,
                body=response.text,
            )
        )

    def get_boleto_inter_pdf(self, provider_id, codigo_solicitacao):
        """Baixa PDF do boleto usando V3"""
        token = self._get_token(provider_id, "cobranca_get")
        base_url = self._inter_get_api_url(provider_id)
        url = base_url + f"cobranca/v3/cobrancas/{codigo_solicitacao}/pdf"
        headers = self._generate_header(token, provider_id)

        try:
            with self._inter_session(provider_id) as session:
                response = session.get(url, headers=headers, timeout=30)
            if response.status_code != 200:
                _logger.warning(
                    "Erro ao baixar PDF do boleto %s: %s",
                    codigo_solicitacao,
                    response.text,
                )
                return ""
            return base64.b64encode(response.content).decode("utf-8")
        except UserError:
            raise
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
        token = self._get_token(provider_id, "cobranca_get")
        base_url = self._inter_get_api_url(provider_id)
        url = f"{base_url}cobranca/v3/cobrancas/{codigo_solicitacao}"
        headers = self._generate_header(token, provider_id)

        try:
            _logger.info("Consultando status do boleto: %s", codigo_solicitacao)
            with self._inter_session(provider_id) as session:
                response = session.get(url, headers=headers, timeout=30)
            _logger.info("Status HTTP: %s", response.status_code)
        except UserError:
            raise
        except Exception as e:
            _logger.error("Erro ao consultar boleto: %s", str(e), exc_info=True)
            raise UserError(_("Erro ao consultar boleto: %s", str(e))) from e

        if response.status_code == 200:
            data = response.json()
            situacao = data.get("cobranca", {}).get("situacao")
            _logger.info("Boleto %s situação atual: %s", codigo_solicitacao, situacao)
            return data
        elif response.status_code == 404:
            raise UserError(
                _(
                    "Boleto não encontrado para codigoSolicitacao %s",
                    codigo_solicitacao,
                )
            )
        elif response.status_code == 401:
            raise UserError(_("Erro de autorização ao consultar boleto no Banco Inter"))
        raise UserError(
            _(
                "Erro ao consultar boleto (%(status)s): %(body)s",
                status=response.status_code,
                body=response.text,
            )
        )

    def cancel_boleto_inter(self, provider_id, codigo_solicitacao):
        """Cancela boleto usando V3"""
        token = self._get_token(provider_id, "cobranca_cancel")
        base_url = self._inter_get_api_url(provider_id)
        url = base_url + f"cobranca/v3/cobrancas/{codigo_solicitacao}/cancelar"
        headers = self._generate_header(token, provider_id)
        vals = {"motivoCancelamento": "SUBSTITUICAO"}

        try:
            with self._inter_session(provider_id) as session:
                response = session.post(url, headers=headers, json=vals, timeout=30)
        except UserError:
            raise
        except Exception as e:
            _logger.error("Erro ao cancelar boleto %s: %s", codigo_solicitacao, str(e))
            raise UserError(_("Erro ao cancelar boleto: %s", str(e))) from e

        if response.status_code not in [200, 204]:
            raise UserError(_("Erro ao cancelar boleto: %s", response.text))
        return True

    def download_boleto_pdf_inter(self, provider, codigo_solicitacao):
        """
        Baixa PDF do boleto Inter e devolve o conteúdo em base64.

        A API responde ora com um JSON contendo o PDF em base64, ora com o
        binário do PDF.
        """
        token = self._get_token(provider, "cobranca_get")
        base_url = self._inter_get_api_url(provider)
        pdf_url = f"{base_url}cobranca/v3/cobrancas/{codigo_solicitacao}/pdf"
        headers = self._generate_header(token, provider)

        try:
            _logger.info("Baixando PDF do boleto: %s", pdf_url)
            with self._inter_session(provider) as session:
                response = session.get(pdf_url, headers=headers, timeout=30)
        except UserError:
            raise
        except Exception as e:
            _logger.exception("Falha ao baixar PDF do boleto")
            raise UserError(_("Erro ao baixar PDF do boleto")) from e

        if response.status_code != 200:
            _logger.error("Erro HTTP %s: %s", response.status_code, response.text)
            raise UserError(
                _(
                    "Erro ao baixar boleto PDF: %(status)s - %(body)s",
                    status=response.status_code,
                    body=response.text,
                )
            )

        return self._inter_extract_pdf(response)

    @staticmethod
    def _inter_extract_pdf(response):
        """Devolve o PDF em base64 a partir da resposta da API.

        :param response: A resposta da requisição do PDF.
        :return: O PDF em base64.
        :rtype: str
        """
        try:
            response_json = response.json()
        except ValueError:
            response_json = None

        if response_json is not None:
            pdf_base64 = response_json.get("pdf")
            if not pdf_base64:
                _logger.error(
                    "JSON não contém chave 'pdf': %s", list(response_json.keys())
                )
                raise UserError(_("Resposta da API não contém PDF"))
            try:
                pdf_content = base64.b64decode(pdf_base64)
            except Exception as decode_error:
                _logger.error("Erro ao decodificar base64: %s", str(decode_error))
                raise UserError(_("PDF retornado está corrompido")) from decode_error
            if not pdf_content.startswith(b"%PDF"):
                _logger.warning("Conteúdo decodificado não parece ser um PDF válido")
            return pdf_base64

        if response.content.startswith(b"%PDF"):
            return base64.b64encode(response.content).decode("utf-8")

        _logger.error("Conteúdo não é PDF nem JSON válido")
        raise UserError(_("Resposta da API não contém PDF"))
