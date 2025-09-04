import logging
import re
from datetime import datetime, timedelta

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _name = "payment.transaction"
    _inherit = ["payment.transaction", "banco.inter.mixin"]

    # BOLETO
    codigo_solicitacao = fields.Char(string="Código Solicitação Inter")
    boleto_reference = fields.Char("Código Solicitação Boleto")

    def generate_boleto(self):
        """Gera boleto compatível com Banco Inter V3"""
        self.ensure_one()
        if self.provider_code != "inter":
            return super().generate_boleto()

        if self.state not in ["draft", "pending"]:
            raise UserError(
                _("Boleto só pode ser gerado para transações em rascunho ou pendentes")
            )

        try:
            boleto_data = self._prepare_boleto_data_inter()
            response = self.add_boleto_inter(self.provider_id, boleto_data)

            if not response or "codigoSolicitacao" not in response:
                raise UserError(_("Resposta do banco não contém codigoSolicitacao"))

            # Salva referência
            self.codigo_solicitacao = response["codigoSolicitacao"]
            self.state = "pending"

            # Baixa PDF automaticamente
            pdf_content = self.download_boleto_pdf_inter(
                self.provider_id, self.codigo_solicitacao
            )
            if pdf_content:
                self.boleto_pdf = pdf_content

            _logger.info(
                "Boleto Inter gerado com sucesso. CodigoSolicitacao: %s",
                self.codigo_solicitacao,
            )

        except Exception as e:
            _logger.error("Erro ao gerar boleto Inter: %s", str(e), exc_info=True)
            raise UserError(_(f"Erro ao gerar boleto Inter: {str(e)}")) from e

    def _prepare_boleto_data_inter(self):
        order = self.sale_order_ids[0] if self.sale_order_ids else None
        invoice = self.invoice_ids[0] if self.invoice_ids else None
        if not invoice and not order:
            raise UserError(
                _("Não é possível gerar boleto sem fatura ou pedido associado")
            )

        # Decide de onde puxar os dados
        partner = (
            invoice.partner_id if invoice else order.partner_id
        ).commercial_partner_id
        payment_mode = invoice.payment_mode_id if invoice else order.payment_mode_id
        company = self.company_id

        # Validação de dados obrigatórios
        self._validate_partner_data(partner)

        # Data de vencimento
        if invoice:
            due_date = (
                self.due_date
                or invoice.invoice_date_due
                or (datetime.now().date() + timedelta(days=30))
            )
        else:
            due_date = self.due_date or (
                order.validity_date or (datetime.now().date() + timedelta(days=30))
            )

        # Valores
        valor_nominal = round(float(self.amount), 2)

        # --- PAGADOR ---
        match_pagador = re.match(r"(.+?),?\s*(\d+)?$", partner.street or "")
        endereco_pagador = (
            match_pagador.group(1).strip()
            if match_pagador
            else (partner.street or "Endereço")
        )
        numero_pagador = (
            match_pagador.group(2) if match_pagador and match_pagador.group(2) else "SN"
        )

        # --- BENEFICIÁRIO ---
        match_benef = re.match(r"(.+?),?\s*(\d+)?$", company.street or "")
        endereco_benef = (
            match_benef.group(1).strip()
            if match_benef
            else (company.street or "Endereço Empresa")
        )
        numero_benef = (
            match_benef.group(2) if match_benef and match_benef.group(2) else "SN"
        )

        # Monta payload
        boleto_data = {
            "seuNumero": self.reference,
            "valorNominal": valor_nominal,
            "valorAbatimento": 0.0,
            "dataVencimento": due_date.strftime("%Y-%m-%d"),
            "numDiasAgenda": 60,
            "pagador": {
                "cpfCnpj": re.sub(r"\D", "", partner.cnpj_cpf or ""),
                "tipoPessoa": "JURIDICA" if partner.is_company else "FISICA",
                "nome": partner.legal_name or partner.name or "Cliente Teste",
                "endereco": endereco_pagador,
                "numero": numero_pagador,
                "complemento": partner.street2 or "",
                "bairro": partner.district or "Bairro Teste",
                "cidade": partner.city_id.name if partner.city_id else "Cidade Teste",
                "uf": partner.state_id.code if partner.state_id else "MG",
                "cep": re.sub(r"\D", "", partner.zip or "00000000"),
                "email": partner.email or "teste@teste.com",
                "ddd": "31",
                "telefone": "999999999",
            },
            "beneficiarioFinal": {
                "cpfCnpj": re.sub(r"\D", "", company.cnpj_cpf or ""),
                "tipoPessoa": "JURIDICA",
                "nome": company.legal_name or company.name,
                "endereco": endereco_benef,
                "numero": numero_benef,
                "bairro": company.district or "",
                "cidade": company.city_id.name if company.city_id else "",
                "uf": company.state_id.code if company.state_id else "",
                "cep": re.sub(r"\D", "", company.zip or "00000000"),
            },
        }

        # Desconto
        if (
            getattr(payment_mode, "payment_boleto_discount", 0) > 0
            and getattr(payment_mode, "payment_boleto_discount_days", 0) > 0
        ):
            boleto_data["desconto"] = {
                "taxa": round(float(payment_mode.payment_boleto_discount), 2),
                "codigo": "PERCENTUALDATAINFORMADA",
                "quantidadeDias": int(payment_mode.payment_boleto_discount_days),
            }

        # Multa
        if getattr(payment_mode, "payment_boleto_penalty", 0) > 0:
            boleto_data["multa"] = {
                "taxa": payment_mode.payment_boleto_penalty * 100,
                "codigo": "PERCENTUAL",
            }

        # Mora / Juros
        if getattr(payment_mode, "payment_boleto_interest", 0) > 0:
            boleto_data["mora"] = {
                "taxa": payment_mode.payment_boleto_interest * 100,
                "codigo": "TAXAMENSAL",
            }

        # Mensagem opcional
        if getattr(payment_mode, "payment_boleto_message_lines", None):
            mensagem = {}
            for i, line in enumerate(
                payment_mode.payment_boleto_message_lines, start=1
            ):
                mensagem[f"linha{i}"] = line
            boleto_data["mensagem"] = mensagem

        return boleto_data

    def action_download_boleto_pdf(self):
        self.ensure_one()
        if self.provider_code != "inter" or not self.codigo_solicitacao:
            raise UserError(_("Ação disponível apenas para boletos do Banco Inter"))
        pdf_content = self.get_boleto_inter_pdf(
            self.provider_id, self.codigo_solicitacao
        )
        if pdf_content:
            self.boleto_pdf = pdf_content
            return {
                "type": "ir.actions.act_url",
                "url": (
                    f"/web/content/payment.transaction/{self.id}/boleto_pdf/"
                    f"boleto_{self.reference}.pdf"
                ),
                "target": "new",
            }
        raise UserError(_("PDF do boleto não disponível"))

    def action_cancel_transaction(self):
        self.ensure_one()
        if self.provider_code != "inter" or not self.codigo_solicitacao:
            raise UserError(
                _("Esta transação não possui código de solicitação do Banco Inter")
            )
        self.cancel_boleto_inter(self.provider_id, self.codigo_solicitacao)
        self.state = "cancel"
        _logger.info("Boleto %s cancelado com sucesso", self.codigo_solicitacao)

    def cron_update_boleto_status(self):
        transactions = self.search(
            [
                ("provider_code", "=", "inter"),
                ("state", "=", "pending"),
                ("codigo_solicitacao", "!=", False),
            ]
        )
        _logger.info("Atualizando status de %d boletos pendentes", len(transactions))

        for tx in transactions:
            try:
                data = tx.get_boleto_status_inter(tx.provider_id, tx.codigo_solicitacao)
                situacao = data.get("cobranca", {}).get("situacao")
                _logger.info(
                    "Transação %s - CódigoSolicitacao %s - Situação: %s",
                    tx.reference,
                    tx.codigo_solicitacao,
                    situacao,
                )
                if situacao == "RECEBIDO":
                    tx.state = "done"
                    _logger.info("Boleto %s marcado como pago.", tx.codigo_solicitacao)
                elif situacao in ["CANCELADO", "VENCIDO"]:
                    tx.state = "cancel"
                    _logger.info(
                        "Boleto %s marcado como cancelado.", tx.codigo_solicitacao
                    )
                # outros status podem permanecer como pending
            except Exception as e:
                _logger.error(
                    "Erro ao atualizar boleto %s: %s", tx.codigo_solicitacao, str(e)
                )

    def _validate_partner_data(self, partner):
        """Valida dados obrigatórios do parceiro"""
        errors = []
        if partner.is_company and not partner.legal_name:
            errors.append("Razão Social")
        if not partner.street:
            errors.append("Endereço - Rua")
        if not partner.street_number:
            errors.append("Endereço - Número")
        if not partner.zip or len(re.sub(r"\D", "", partner.zip)) != 8:
            errors.append("Endereço - CEP")
        if not partner.state_id:
            errors.append("Endereço - Estado")
        if not partner.city_id:
            errors.append("Endereço - Município")
        if not partner.cnpj_cpf:
            errors.append("CPF/CNPJ")

        if errors:
            raise ValidationError(
                _(
                    f"Dados obrigatórios ausentes no parceiro '{partner.name}':\n"
                    + "\n".join(f"• {err}" for err in errors)
                )
            )

    def _get_processing_values(self):
        res = super()._get_processing_values()
        if self.provider_code != "inter":
            return res

        if self.provider_code == "inter":
            if not self.codigo_solicitacao:
                self.generate_boleto()
            if not self.boleto_pdf:
                raise UserError(_("Boleto PDF não disponível"))

            boleto_url = f"/payment/boleto/{self.id}"
            res.update(
                {
                    "redirect_url": boleto_url,
                    "redirect_form_html": self.env["ir.ui.view"]._render_template(
                        "l10n_br_payment_boleto_inter.boleto_inter_redirect_template",
                        {"redirect_url": boleto_url},
                    ),
                }
            )

        return res
