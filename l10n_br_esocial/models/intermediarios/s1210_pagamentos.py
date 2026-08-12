# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

# Tabela 22 do leiaute — tipos de pagamento relevantes ao ciclo mínimo.
TP_PGTO = [
    ("1", "1 - Pagamento de remuneração (S-1200)"),
    ("2", "2 - Pagamento de benefício previdenciário (S-1202)"),
    ("3", "3 - Pagamento a beneficiário sem vínculo (S-1207)"),
    ("4", "4 - Pagamento de verbas rescisórias (S-2299)"),
    ("5", "5 - Pagamento de verbas rescisórias de TSV (S-2399)"),
]


class ESocialS1210(models.Model):
    _name = "l10n_br.esocial.s1210"
    _inherit = "l10n_br.esocial.base.intermediario"
    _description = "eSocial S-1210 - Pagamentos de Rendimentos do Trabalho"
    _order = "per_apur desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    employee_id = fields.Many2one(
        "hr.employee",
        string="Beneficiário",
        required=True,
        ondelete="cascade",
    )
    per_apur = fields.Char(
        string="Período Apuração",
        size=7,
        required=True,
        help="Competência do PAGAMENTO (regime de caixa), formato AAAA-MM. "
        "Não confundir com a competência da folha, que vai em cada "
        "demonstrativo no campo Período de Referência.",
    )
    ind_retif = fields.Selection(
        [
            ("1", "Original"),
            ("2", "Retificação"),
        ],
        string="Indicativo Retificação",
        default="1",
        required=True,
    )
    nr_recibo = fields.Char(
        string="Nº Recibo Retificado",
        help="Recibo do S-1210 a ser retificado. Obrigatório quando o "
        "Indicativo de Retificação for 'Retificação'.",
    )
    pagamento_ids = fields.One2many(
        "l10n_br.esocial.s1210.pagamento",
        "s1210_id",
        string="Pagamentos",
    )
    vr_liq_total = fields.Monetary(
        string="Total Líquido Pago",
        compute="_compute_vr_liq_total",
        store=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        readonly=True,
    )

    @api.depends("employee_id", "per_apur")
    def _compute_name(self):
        for rec in self:
            rec.name = " - ".join(
                parte for parte in (rec.employee_id.name, rec.per_apur) if parte
            )

    @api.depends("pagamento_ids.vr_liq")
    def _compute_vr_liq_total(self):
        for rec in self:
            rec.vr_liq_total = sum(rec.pagamento_ids.mapped("vr_liq"))

    @api.constrains("per_apur")
    def _check_per_apur(self):
        for rec in self:
            rec._validar_competencia(rec.per_apur, _("Período Apuração"))

    @api.constrains("nr_recibo")
    def _check_nr_recibo(self):
        for rec in self:
            rec._validar_nr_recibo(rec.nr_recibo, _("Nº Recibo Retificado"))

    def _get_event_type(self):
        return "S-1210"

    def _prepare_evento_vals(self, xml, id_evento):
        vals = super()._prepare_evento_vals(xml, id_evento)
        vals.update(
            {
                "per_apur": self.per_apur,
                "ind_retif": self.ind_retif,
                "operacao": "R" if self.ind_retif == "2" else "I",
            }
        )
        return vals

    def _to_esociallib_dict(self):
        self.ensure_one()
        employee = self.employee_id

        cpf = employee.cnpj_cpf
        if not cpf:
            raise UserError(
                _("Beneficiário '%(name)s' não possui CPF configurado.")
                % {"name": employee.name}
            )

        if not self.pagamento_ids:
            raise UserError(
                _(
                    "S-1210 de %(name)s (%(per)s) não possui pagamentos. O "
                    "evento informa pagamentos efetivamente realizados: gere-o "
                    "a partir dos holerites pagos."
                )
                % {"name": employee.name, "per": self.per_apur}
            )

        ind_retif = int(self.ind_retif)
        if ind_retif == 2 and not self.nr_recibo:
            raise UserError(
                _(
                    "Retificação (ind_retif=2) exige o Nº do Recibo do S-1210 "
                    "original a ser retificado."
                )
            )

        ide = self._get_ide_empregador()
        proc = self._get_proc_info()

        data = {
            "tp_insc": ide["tp_insc"],
            "nr_insc": ide["nr_insc"],
            "per_apur": self.per_apur,
            "ind_retif": ind_retif,
            "proc_emi": proc["proc_emi"],
            "ver_proc": proc["ver_proc"],
            "cpf_benef": self._so_digitos(cpf),
            "info_pgto": [
                pagamento._to_esociallib_dict()
                for pagamento in self.pagamento_ids.sorted("dt_pgto")
            ],
        }
        if ind_retif == 2:
            data["nr_recibo"] = self.nr_recibo
        return data


class ESocialS1210Pagamento(models.Model):
    _name = "l10n_br.esocial.s1210.pagamento"
    _description = "eSocial S-1210 - Pagamento (infoPgto)"
    _order = "dt_pgto, id"

    s1210_id = fields.Many2one(
        "l10n_br.esocial.s1210",
        string="S-1210",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        related="s1210_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="s1210_id.currency_id",
        readonly=True,
    )
    dt_pgto = fields.Date(
        string="Data Pagamento",
        required=True,
    )
    tp_pgto = fields.Selection(
        TP_PGTO,
        string="Tipo Pagamento",
        default="1",
        required=True,
    )
    per_ref = fields.Char(
        string="Período Referência",
        size=7,
        required=True,
        help="Competência da folha que originou o pagamento (AAAA-MM) ou o ano "
        "(AAAA) no caso do 13º salário.",
    )
    ide_dm_dev = fields.Char(
        string="Demonstrativo",
        size=30,
        required=True,
        help="Identificador do demonstrativo (ideDmDev) informado no S-1200 da "
        "competência de referência.",
    )
    vr_liq = fields.Monetary(
        string="Valor Líquido",
        required=True,
        currency_field="currency_id",
    )
    payslip_id = fields.Many2one(
        "hr.payslip",
        string="Holerite",
        ondelete="set null",
    )
    s1200_id = fields.Many2one(
        "l10n_br.esocial.s1200",
        string="S-1200 de Origem",
        ondelete="set null",
        help="Apuração que este pagamento liquida. É dela que sai o "
        "identificador do demonstrativo.",
    )

    @api.constrains("per_ref")
    def _check_per_ref(self):
        base = self.env["l10n_br.esocial.base.intermediario"]
        for rec in self:
            base._validar_competencia(rec.per_ref, _("Período Referência"), anual=True)

    @api.constrains("vr_liq")
    def _check_vr_liq(self):
        for rec in self:
            if rec.vr_liq <= 0:
                raise ValidationError(
                    _(
                        "Pagamento de %(data)s: o valor líquido pago deve ser "
                        "positivo (informado: %(valor)s). Holerite com líquido "
                        "zero ou negativo não gera pagamento no S-1210."
                    )
                    % {"data": rec.dt_pgto, "valor": rec.vr_liq}
                )

    def _to_esociallib_dict(self):
        self.ensure_one()
        return {
            "dt_pgto": fields.Date.to_string(self.dt_pgto),
            "tp_pgto": int(self.tp_pgto),
            "per_ref": self.per_ref,
            "ide_dm_dev": self.ide_dm_dev,
            "vr_liq": "%.2f" % self.vr_liq,
        }
