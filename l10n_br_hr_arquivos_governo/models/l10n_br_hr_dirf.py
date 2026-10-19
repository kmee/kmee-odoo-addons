# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import calendar
import io
import unicodedata

from odoo import _, api, fields, models
from odoo.exceptions import UserError


def _normalize(text, size=0, fill=" "):
    """Remove acentos e ajusta tamanho do campo."""
    if not text:
        text = ""
    text = unicodedata.normalize("NFKD", str(text))
    text = text.encode("ASCII", "ignore").decode("ASCII")
    if size:
        text = text[:size].ljust(size, fill)
    return text


def _format_value(value):
    """Formata valor monetário para DIRF (centavos, sem separador)."""
    return str(int(round(abs(value) * 100, 0))).zfill(15)


class HrDirf(models.Model):
    """DIRF descontinuada.

    A obrigação foi extinta pela IN RFB 2.181/2024 (fatos a partir de
    01/01/2025 vão por EFD-Reinf/eSocial, com confissão e recolhimento na
    DCTFWeb). O modelo é mantido apenas para consulta do histórico já
    gerado: a ação de geração está bloqueada e o código de montagem do
    arquivo abaixo não é mais executado.
    """

    _name = "l10n_br.hr.dirf"
    _description = "DIRF - Declaração do IR Retido na Fonte (descontinuada)"
    _order = "ano_referencia desc"

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
    ano_referencia = fields.Integer(
        string="Ano de Referência",
        required=True,
    )
    ano_calendario = fields.Integer(
        string="Ano Calendário",
        required=True,
    )
    retificadora = fields.Boolean(
        string="Declaração Retificadora",
        default=False,
    )
    numero_recibo = fields.Char(
        string="Número do Recibo (retificação)",
    )
    employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        string="Funcionários",
    )
    file_content = fields.Text(
        string="Conteúdo DIRF",
        readonly=True,
    )
    file_binary = fields.Binary(
        string="Arquivo DIRF",
        readonly=True,
    )
    file_name = fields.Char(
        string="Nome do Arquivo",
    )

    @api.depends("ano_referencia", "company_id")
    def _compute_name(self):
        for rec in self:
            rec.name = "DIRF %s - %s" % (
                rec.ano_referencia or "",
                rec.company_id.name or "",
            )

    def action_draft(self):
        self.write({"state": "draft"})

    def action_open(self):
        self.write({"state": "open"})

    def action_sent(self):
        self.write({"state": "sent"})

    def action_buscar_funcionarios(self):
        """Busca funcionários com holerites no ano de referência."""
        self.ensure_one()
        payslips = self.env["hr.payslip"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("date_from", ">=", "%d-01-01" % self.ano_calendario),
                ("date_from", "<=", "%d-12-31" % self.ano_calendario),
                ("state", "in", ["done", "paid"]),
            ]
        )
        employees = payslips.mapped("employee_id")
        self.employee_ids = employees
        return True

    def _get_payslips_employee(self, employee, month=None):
        """Busca holerites de um empregado no ano calendário."""
        domain = [
            ("employee_id", "=", employee.id),
            ("company_id", "=", self.company_id.id),
            ("date_from", ">=", "%d-01-01" % self.ano_calendario),
            ("date_from", "<=", "%d-12-31" % self.ano_calendario),
            ("state", "in", ["done", "paid"]),
        ]
        if month:
            domain.append(
                ("date_from", ">=", "%d-%02d-01" % (self.ano_calendario, month))
            )
            last_day = calendar.monthrange(self.ano_calendario, month)[1]
            domain.append(
                (
                    "date_from",
                    "<=",
                    "%d-%02d-%02d" % (self.ano_calendario, month, last_day),
                )
            )
        return self.env["hr.payslip"].search(domain)

    def _get_line_total(self, payslips, code):
        """Soma o total de uma rubrica nos holerites."""
        total = 0.0
        for payslip in payslips:
            for line in payslip.line_ids:
                if line.code == code:
                    total += line.total
        return total

    def _generate_header(self):
        """Gera cabeçalho DIRF."""
        lines = []
        lines.append("DIRF|%d|%d|N||" % (self.ano_referencia, self.ano_calendario))
        # RESPO - responsável
        company = self.company_id
        partner = company.partner_id
        cpf_resp = (
            (partner.cnpj_cpf or "").replace(".", "").replace("-", "").replace("/", "")
        )
        lines.append(
            "RESPO|%s|%s|%s|%s|"
            % (
                cpf_resp[:11].zfill(11),
                _normalize(partner.name, 60),
                "0",
                "",
            )
        )
        # DECPJ - declarante PJ
        cnpj = (
            (partner.cnpj_cpf or "").replace(".", "").replace("-", "").replace("/", "")
        )
        lines.append(
            "DECPJ|%s|%s|0|N|N|N|N|N|N|N|0|N|N|"
            % (
                cnpj[:14].zfill(14),
                _normalize(company.name, 150),
            )
        )
        return lines

    def _generate_employee_data(self, employee):
        """Gera dados DIRF de um empregado."""
        lines = []
        payslips = self._get_payslips_employee(employee)
        if not payslips:
            return lines

        cpf = (employee.cnpj_cpf or "").replace(".", "").replace("-", "")

        # IDREC - código de receita (0561 = empregado CLT)
        lines.append("IDREC|0561|")

        # BPFDEC - beneficiário pessoa física
        lines.append(
            "BPFDEC|%s|%s|N|N|N|N|N|N|N|N|"
            % (
                cpf[:11].zfill(11),
                _normalize(employee.name, 60),
            )
        )

        # RTRT - Rendimentos tributáveis por mês
        for month in range(1, 13):
            month_payslips = self._get_payslips_employee(employee, month)
            rendimento = self._get_line_total(month_payslips, "BRUTO")
            lines.append("RTRT|%s|" % _format_value(rendimento))

        # RTPO - Previdência oficial por mês
        for month in range(1, 13):
            month_payslips = self._get_payslips_employee(employee, month)
            inss = self._get_line_total(month_payslips, "INSS")
            lines.append("RTPO|%s|" % _format_value(inss))

        # RTDP - IR retido por mês
        for month in range(1, 13):
            month_payslips = self._get_payslips_employee(employee, month)
            irrf = self._get_line_total(month_payslips, "IRRF")
            lines.append("RTDP|%s|" % _format_value(irrf))

        return lines

    def action_gerar_dirf(self):
        """Bloqueado: a DIRF foi extinta (ver docstring da classe)."""
        raise UserError(
            _(
                "A DIRF foi extinta e este gerador foi descontinuado.\n\n"
                "Norma: IN RFB 2.181/2024, que encerrou a DIRF. Para os fatos "
                "ocorridos a partir de 1o de janeiro de 2025 não há mais "
                "entrega de DIRF.\n\n"
                "Caminho atual: as retenções de imposto de renda na fonte são "
                "informadas pela EFD-Reinf (eventos da série R-4000) e pelo "
                "eSocial, e a confissão e o recolhimento passam pela DCTFWeb. "
                "O comprovante anual de rendimentos ao beneficiário continua "
                "devido e não depende deste gerador.\n\n"
                "Os registros de DIRF já existentes continuam disponíveis "
                "somente para consulta de histórico."
            )
        )

    def _gerar_dirf_descontinuado(self):
        """Código morto mantido como referência do leiaute antigo da DIRF.

        Não é chamado por nenhuma ação: a geração está bloqueada em
        :meth:`action_gerar_dirf`.
        """
        self.ensure_one()
        if not self.employee_ids:
            raise UserError(_("Busque os funcionários antes de gerar a DIRF."))

        lines = self._generate_header()
        for employee in self.employee_ids:
            lines.extend(self._generate_employee_data(employee))

        lines.append("FIMDirf|")
        content = "\r\n".join(lines)

        buf = io.BytesIO()
        buf.write(content.encode("ascii", "ignore"))

        self.write(
            {
                "file_content": content,
                "file_binary": base64.b64encode(buf.getvalue()),
                "file_name": "DIRF_%d_%s.txt"
                % (
                    self.ano_referencia,
                    (self.company_id.partner_id.cnpj_cpf or "")
                    .replace(".", "")
                    .replace("-", "")
                    .replace("/", ""),
                ),
                "state": "open",
            }
        )
        return True
