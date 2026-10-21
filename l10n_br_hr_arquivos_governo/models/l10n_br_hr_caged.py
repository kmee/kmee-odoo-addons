# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import calendar
import io
import unicodedata

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .constantes_rh import MESES


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


class L10nBrHrCaged(models.Model):
    """CAGED descontinuado.

    O CAGED foi extinto: desde janeiro de 2020 (Portaria SEPRT 1.127/2019)
    as movimentações são informadas pelo eSocial (S-2200 e S-2299), que
    alimenta o Novo CAGED. O modelo é mantido apenas para consulta do
    histórico já gerado: a ação de geração está bloqueada e o código de
    montagem do arquivo abaixo não é mais executado.
    """

    _name = "l10n_br.hr.caged"
    _description = "CAGED - Cadastro de Empregados e Desempregados (descontinuado)"
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
        selection=MESES[:12],
        string="Mês",
        required=True,
    )
    ano = fields.Integer(
        required=True,
    )
    primeira_declaracao = fields.Boolean(
        string="Primeira Declaração",
        default=False,
    )
    responsavel = fields.Char(
        string="Responsável",
    )
    cpf_responsavel = fields.Char(
        string="CPF do Responsável",
        size=14,
    )
    email_responsavel = fields.Char(
        string="E-mail do Responsável",
    )
    contract_ids = fields.Many2many(
        comodel_name="hr.contract",
        string="Movimentações",
        readonly=True,
    )
    file_content = fields.Text(
        string="Conteúdo CAGED",
        readonly=True,
    )
    file_binary = fields.Binary(
        string="Arquivo CAGED",
        readonly=True,
    )
    file_name = fields.Char(
        string="Nome do Arquivo",
    )

    @api.depends("mes", "ano", "company_id")
    def _compute_name(self):
        for rec in self:
            mes_label = dict(MESES[:12]).get(rec.mes, "")
            rec.name = "CAGED %s/%s - %s" % (
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

    def _buscar_movimentacoes(self):
        """Busca contratos com admissão ou demissão no período."""
        self.ensure_one()
        mes = int(self.mes)
        last_day = calendar.monthrange(self.ano, mes)[1]
        date_start = "%d-%02d-01" % (self.ano, mes)
        date_end = "%d-%02d-%02d" % (self.ano, mes, last_day)

        # Admissões no mês
        admissoes = self.env["hr.contract"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("date_start", ">=", date_start),
                ("date_start", "<=", date_end),
            ]
        )
        # Demissões no mês
        demissoes = self.env["hr.contract"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("date_end", ">=", date_start),
                ("date_end", "<=", date_end),
                ("state", "in", ["close", "cancel"]),
            ]
        )
        return admissoes | demissoes

    def action_gerar_caged(self):
        """Bloqueado: o CAGED foi extinto (ver docstring da classe)."""
        raise UserError(
            _(
                "O CAGED foi extinto e este gerador foi descontinuado.\n\n"
                "Norma: Portaria SEPRT 1.127/2019, que dispensou a declaração "
                "do CAGED para quem presta informações pelo eSocial. Desde "
                "janeiro de 2020 não há mais entrega do arquivo CAGED.\n\n"
                "Caminho atual: as admissões e os desligamentos são informados "
                "pelos eventos S-2200 (admissão) e S-2299 (desligamento) do "
                "eSocial, que alimentam o Novo CAGED.\n\n"
                "Os registros de CAGED já existentes continuam disponíveis "
                "somente para consulta de histórico."
            )
        )

    def _gerar_caged_descontinuado(self):
        """Código morto mantido como referência do leiaute antigo do CAGED.

        Não é chamado por nenhuma ação: a geração está bloqueada em
        :meth:`action_gerar_caged`.
        """
        self.ensure_one()
        contracts = self._buscar_movimentacoes()
        if not contracts:
            raise UserError(
                _("Nenhuma movimentação encontrada para %(mes)s/%(ano)s.")
                % {"mes": self.mes, "ano": self.ano}
            )

        self.contract_ids = contracts

        lines = []
        company = self.company_id
        partner = company.partner_id
        cnpj = (
            (partner.cnpj_cpf or "").replace(".", "").replace("-", "").replace("/", "")
        )

        # Registro A - Estabelecimento autorizado
        lines.append(
            "A"
            + ("1" if self.primeira_declaracao else "2")
            + _num(len(contracts), 5)
            + _normalize(self.responsavel or partner.name, 40)
            + _normalize(self.email_responsavel or "", 50)
        )

        # Registro B - Dados do estabelecimento
        lines.append(
            "B"
            + cnpj[:14].ljust(14, "0")
            + _normalize(company.name, 40)
            + _normalize(partner.street or "", 50)
            + _normalize(partner.city or "", 30)
            + (partner.state_id.code or "SP").ljust(2)
            + (partner.zip or "").replace("-", "").ljust(8, "0")
        )

        # Registro C - Movimentações
        for contract in contracts:
            employee = contract.employee_id
            cpf = (employee.cnpj_cpf or "").replace(".", "").replace("-", "")
            pis = (employee.pis_pasep or "").replace(".", "").replace("-", "")

            # Tipo: 10=admissão, 20=desligamento
            is_admission = contract.date_start and str(contract.date_start)[
                :7
            ] == "%d-%02d" % (self.ano, int(self.mes))
            tipo = "10" if is_admission else "20"

            lines.append(
                "C"
                + tipo
                + pis[:11].ljust(11, "0")
                + cpf[:11].ljust(11, "0")
                + _normalize(employee.name, 40)
                + str(int(contract.wage or 0)).zfill(10)
                + (str(contract.date_start or "").replace("-", ""))[:8].ljust(8, "0")
            )

        # Registro Z - Trailer
        lines.append(
            "Z"
            + _normalize(self.responsavel or partner.name, 40)
            + _normalize(self.email_responsavel or "", 50)
            + _num(len(contracts), 5)
        )

        content = "\r\n".join(lines)
        buf = io.BytesIO()
        buf.write(content.encode("ascii", "ignore"))

        self.write(
            {
                "file_content": content,
                "file_binary": base64.b64encode(buf.getvalue()),
                "file_name": "CAGED_%02d_%d_%s.txt"
                % (
                    int(self.mes),
                    self.ano,
                    cnpj,
                ),
                "state": "open",
            }
        )
        return True
