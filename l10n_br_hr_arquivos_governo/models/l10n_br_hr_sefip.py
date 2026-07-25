import base64
import calendar
import io
import unicodedata

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .constantes_rh import (
    CENTRALIZADORA,
    CODIGO_RECOLHIMENTO,
    CODIGOS_FGTS,
    CODIGOS_INSS,
    CODIGOS_REMUNERACAO_BRUTA,
    MESES,
    MODALIDADE_ARQUIVO,
    RECOLHIMENTO_FGTS,
    RECOLHIMENTO_GPS,
)
from .rubricas import somar_rubricas


def _normalize(text, size, fill=" "):
    """Remove acentos e preenche até o tamanho."""
    if not text:
        text = ""
    text = unicodedata.normalize("NFKD", str(text))
    text = text.encode("ASCII", "ignore").decode("ASCII")
    return text[:size].ljust(size, fill)


def _num(value, size):
    """Formata número com zeros à esquerda."""
    return str(int(value or 0)).zfill(size)[:size]


def _val(value, size):
    """Formata valor monetário (centavos) com zeros à esquerda."""
    return str(int(round(abs(value or 0) * 100, 0))).zfill(size)[:size]


class L10nBrHrSefip(models.Model):
    _name = "l10n_br.hr.sefip"
    _description = "SEFIP - FGTS e Previdência Social"
    _order = "ano desc, mes desc"

    name = fields.Char(
        string="Nome",
        compute="_compute_name",
        store=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Rascunho"),
            ("open", "Aberto"),
            ("sent", "Enviado"),
        ],
        default="draft",
        string="Situação",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )
    mes = fields.Selection(
        selection=MESES,
        string="Competência (Mês)",
        required=True,
    )
    ano = fields.Integer(
        string="Competência (Ano)",
        required=True,
    )
    codigo_recolhimento = fields.Selection(
        selection=CODIGO_RECOLHIMENTO,
        string="Código de Recolhimento",
        default="115",
        required=True,
    )
    modalidade_arquivo = fields.Selection(
        selection=MODALIDADE_ARQUIVO,
        string="Modalidade do Arquivo",
        default=" ",
    )
    recolhimento_fgts = fields.Selection(
        selection=RECOLHIMENTO_FGTS,
        string="Recolhimento FGTS",
        default="1",
    )
    recolhimento_gps = fields.Selection(
        selection=RECOLHIMENTO_GPS,
        string="Recolhimento GPS",
        default="1",
    )
    centralizadora = fields.Selection(
        selection=CENTRALIZADORA,
        string="Centralização",
        default="0",
    )
    codigo_fpas = fields.Char(
        string="Código FPAS",
        size=3,
        default="515",
    )
    codigo_outras_entidades = fields.Char(
        string="Código Outras Entidades",
        size=4,
    )
    payslip_ids = fields.Many2many(
        comodel_name="hr.payslip",
        string="Holerites",
        readonly=True,
    )
    file_content = fields.Text(
        string="Conteúdo SEFIP",
        readonly=True,
    )
    file_binary = fields.Binary(
        string="Arquivo SEFIP",
        readonly=True,
    )
    file_name = fields.Char(
        string="Nome do Arquivo",
    )

    @api.depends("mes", "ano", "company_id")
    def _compute_name(self):
        for rec in self:
            mes_label = dict(MESES).get(rec.mes, "")
            rec.name = "SEFIP %s/%s - %s" % (
                mes_label,
                rec.ano or "",
                rec.company_id.name or "",
            )

    def action_draft(self):
        self.write({"state": "draft"})

    def action_open(self):
        self.write({"state": "open"})

    def action_sent(self):
        self.write({"state": "sent"})

    def _buscar_holerites(self):
        """Busca holerites da competência."""
        self.ensure_one()
        mes = int(self.mes)
        domain = [
            ("company_id", "=", self.company_id.id),
            ("state", "in", ["done", "paid"]),
        ]
        if mes <= 12:
            last_day = calendar.monthrange(self.ano, mes)[1]
            domain += [
                ("date_from", ">=", "%d-%02d-01" % (self.ano, mes)),
                ("date_from", "<=", "%d-%02d-%02d" % (self.ano, mes, last_day)),
            ]
        return self.env["hr.payslip"].search(domain)

    def _get_line_total(self, payslips, codigos):
        """Retorna o total de uma rubrica nos holerites.

        ``codigos`` pode ser um código único ou uma coleção de códigos
        equivalentes (ex.: ``INSS`` na folha mensal e ``INSS_13`` no 13º,
        somados quando ambos existem, como na rescisão).  Holerites sem
        nenhuma linha com esses códigos geram aviso explícito no log.
        """
        total, _faltantes = somar_rubricas(payslips, codigos, origem="SEFIP")
        return abs(total)

    def _generate_reg00(self):
        """Registro 00 - Header."""
        company = self.company_id
        partner = company.partner_id
        (partner.cnpj_cpf or "").replace(".", "").replace("-", "").replace("/", "")
        return (
            "00"
            + " " * 51  # responsável (simplificado)
            + _normalize(partner.name, 30)
            + " " * 79  # campos complementares
        )

    def _generate_reg10(self):
        """Registro 10 - Empresa."""
        company = self.company_id
        partner = company.partner_id
        cnpj = (
            (partner.cnpj_cpf or "").replace(".", "").replace("-", "").replace("/", "")
        )
        return (
            "10"
            + " "  # tipo inscricao (1=CNPJ)
            + cnpj[:14].ljust(14, "0")
            + "0" * 36  # zeros
            + _normalize(company.name, 40)
            + " " * 205  # endereco e complementos
            + (self.codigo_fpas or "515").ljust(3)
            + (self.codigo_outras_entidades or "0000").ljust(4)
        )

    def action_gerar_sefip(self):
        """Gera o arquivo SEFIP."""
        self.ensure_one()
        payslips = self._buscar_holerites()
        if not payslips:
            raise UserError(
                _("Nenhum holerite encontrado para %(mes)s/%(ano)s.")
                % {"mes": self.mes, "ano": self.ano}
            )

        self.payslip_ids = payslips

        lines = []
        lines.append(self._generate_reg00())
        lines.append(self._generate_reg10())

        # Registro 30 - Trabalhadores (simplificado)
        total_remuneracao = 0.0
        for payslip in payslips:
            employee = payslip.employee_id
            pis = (employee.pis_pasep or "").replace(".", "").replace("-", "")
            remuneracao = self._get_line_total(payslip, CODIGOS_REMUNERACAO_BRUTA)
            inss_desc = self._get_line_total(payslip, CODIGOS_INSS)
            fgts = self._get_line_total(payslip, CODIGOS_FGTS)
            total_remuneracao += remuneracao

            line = (
                "30"
                + pis[:11].ljust(11, "0")
                + _normalize(employee.name, 70)
                + _val(remuneracao, 15)
                + _val(inss_desc, 15)
                + _val(fgts, 15)
                + "01"  # ocorrência
                + " " * 50  # complemento
            )
            lines.append(line)

        # Falha alta: SEFIP com remuneração total zerada em todos os
        # trabalhadores indica rubrica ausente/errada, não arquivo válido.
        if not total_remuneracao:
            raise UserError(
                _(
                    "Nenhuma remuneração encontrada nos %(qtd)s holerite(s) da "
                    "competência %(mes)s/%(ano)s.\n\n"
                    "O SEFIP não foi gerado para evitar um arquivo zerado. "
                    "Confira se as regras salariais da folha possuem as rubricas "
                    "%(codigos)s."
                )
                % {
                    "qtd": len(payslips),
                    "mes": self.mes,
                    "ano": self.ano,
                    "codigos": "/".join(CODIGOS_REMUNERACAO_BRUTA),
                }
            )

        content = "\r\n".join(lines)
        buf = io.BytesIO()
        buf.write(content.encode("ascii", "ignore"))

        self.write(
            {
                "file_content": content,
                "file_binary": base64.b64encode(buf.getvalue()),
                "file_name": "SEFIP_%02d_%d_%s.txt"
                % (
                    int(self.mes),
                    self.ano,
                    (self.company_id.partner_id.cnpj_cpf or "")
                    .replace(".", "")
                    .replace("-", "")
                    .replace("/", ""),
                ),
                "state": "open",
            }
        )
        return True
