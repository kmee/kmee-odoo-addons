# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.l10n_br_hr_sst.models.sst_dominios import SIM_NAO

# Antecedência padrão do alerta de vencimento do CA, em dias.
DIAS_ALERTA_VENCIMENTO = 60


class L10nBrSstCa(models.Model):
    """Certificado de Aprovação do EPI (NR-6).

    O CA é entidade própria, e não um número solto na entrega: a validade é do
    fabricante e independe da data em que o EPI foi entregue, de modo que o
    vencimento de um CA atinge de uma vez todas as entregas que dependem dele.
    O número do CA é o que vai no campo ``docAval`` do S-2240.
    """

    _name = "l10n_br.sst.ca"
    _description = "SST - Certificado de Aprovação (CA)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "validade desc, numero"
    _rec_name = "name"

    name = fields.Char(
        string="Certificado",
        compute="_compute_name",
        store=True,
    )
    numero = fields.Char(
        string="Número do CA",
        required=True,
        tracking=True,
        help="Número do Certificado de Aprovação emitido pelo Ministério do "
        "Trabalho. Informado em docAval no S-2240.",
    )
    validade = fields.Date(
        string="Validade do Certificado",
        required=True,
        tracking=True,
    )
    fabricante_id = fields.Many2one(
        "res.partner",
        string="Fabricante",
    )
    fabricante = fields.Char(
        string="Fabricante (texto)",
        help="Use quando o fabricante não tem cadastro de parceiro.",
    )
    descricao_epi = fields.Char(
        string="Descrição do EPI",
        required=True,
        help="Descrição do equipamento, informada em dscEPI no S-2240.",
    )
    tipo_epi = fields.Char(
        string="Tipo de EPI",
        help="Classificação do equipamento, por exemplo protetor auricular.",
    )
    risco_neutralizado_ids = fields.Many2many(
        "l10n_br.sst.risco",
        relation="l10n_br_sst_ca_risco_rel",
        column1="ca_id",
        column2="risco_id",
        string="Riscos Neutralizados",
        help="Fatores de risco que este EPI protege. É o que liga a entrega do "
        "equipamento ao grupo epcEpi do S-2240.",
    )
    agente_nocivo_ids = fields.Many2many(
        "l10n_br.esocial.agente.nocivo",
        string="Agentes Nocivos",
        compute="_compute_agente_nocivo_ids",
        store=True,
    )
    product_ids = fields.One2many(
        "product.template",
        "l10n_br_sst_ca_id",
        string="Produtos",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        default=lambda self: self.env.company,
    )
    state = fields.Selection(
        [
            ("vigente", "Vigente"),
            ("a_vencer", "A Vencer"),
            ("vencido", "Vencido"),
        ],
        string="Situação",
        compute="_compute_state",
        store=True,
    )
    observacao = fields.Text(string="Observações")
    active = fields.Boolean(default=True)
    # ── Grupo epiCompl do S-2240 ───────────────────────────────────────────
    # São as declarações que o empregador faz sobre as condições de uso do
    # equipamento. Ficam no CA porque descrevem o EPI, não o risco: o mesmo
    # protetor auricular tem a mesma exigência de troca em qualquer ambiente.
    med_protecao = fields.Selection(
        SIM_NAO,
        string="Medidas de Proteção Adotadas",
        default="S",
        help="Foram observadas as condições de funcionamento do EPI ao longo "
        "do tempo, conforme especificação técnica do fabricante.",
    )
    cond_functo = fields.Selection(
        SIM_NAO,
        string="Condições de Funcionamento",
        default="S",
    )
    uso_inint = fields.Selection(
        SIM_NAO,
        string="Uso Ininterrupto",
        default="S",
    )
    prz_valid = fields.Selection(
        SIM_NAO,
        string="Prazo de Validade Observado",
        default="S",
    )
    periodic_troca = fields.Selection(
        SIM_NAO,
        string="Periodicidade de Troca Observada",
        default="S",
    )
    higienizacao = fields.Selection(
        SIM_NAO,
        string="Higienização Observada",
        default="S",
    )

    _sql_constraints = [
        (
            "numero_uniq",
            "unique(numero, company_id)",
            "Já existe um Certificado de Aprovação com este número.",
        ),
    ]

    @api.depends("numero", "descricao_epi")
    def _compute_name(self):
        for rec in self:
            partes = [
                p for p in (rec.numero and "CA %s" % rec.numero, rec.descricao_epi) if p
            ]
            rec.name = " - ".join(partes)

    @api.depends("risco_neutralizado_ids.agente_nocivo_id")
    def _compute_agente_nocivo_ids(self):
        for rec in self:
            rec.agente_nocivo_ids = rec.risco_neutralizado_ids.mapped(
                "agente_nocivo_id"
            )

    @api.depends("validade")
    def _compute_state(self):
        hoje = fields.Date.context_today(self)
        limite = fields.Date.add(hoje, days=DIAS_ALERTA_VENCIMENTO)
        for rec in self:
            if not rec.validade:
                rec.state = "vigente"
            elif rec.validade < hoje:
                rec.state = "vencido"
            elif rec.validade <= limite:
                rec.state = "a_vencer"
            else:
                rec.state = "vigente"

    @api.constrains("numero")
    def _check_numero(self):
        for rec in self:
            if not (rec.numero or "").strip():
                raise ValidationError(
                    _("Informe o número do Certificado de Aprovação.")
                )

    def _vigente_em(self, data=None):
        """Diz se o CA está válido na data informada (hoje, por padrão)."""
        self.ensure_one()
        data = fields.Date.to_date(data) or fields.Date.context_today(self)
        return bool(self.validade) and self.validade >= data

    @api.model
    def cron_alerta_vencimento(self):
        """Recalcula a situação dos CAs e registra o vencimento no chatter.

        O cron do ``hr_employee_ppe`` expira a alocação pela data de entrega; o
        que falta, e é o que a NR-6 cobra, é enxergar o CA que caducou levando
        junto todas as entregas que dependiam dele.
        """
        cas = self.search([("validade", "!=", False)])
        cas._compute_state()
        for ca in cas.filtered(lambda c: c.state in ("a_vencer", "vencido")):
            entregas = self.env["hr.personal.equipment"].search(
                [
                    ("l10n_br_sst_ca_id", "=", ca.id),
                    ("state", "=", "valid"),
                ]
            )
            if not entregas:
                continue
            ca.message_post(
                body=_(
                    "Certificado de Aprovação %(situacao)s em %(validade)s com "
                    "%(qtd)s entrega(s) de EPI ainda válidas."
                )
                % {
                    "situacao": dict(self._fields["state"].selection)[ca.state],
                    "validade": ca.validade,
                    "qtd": len(entregas),
                }
            )
        return True
