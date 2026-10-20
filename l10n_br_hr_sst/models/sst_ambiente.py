# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .sst_dominios import LOCAL_AMBIENTE, TP_INSC_ESTABELECIMENTO


class L10nBrSstAmbiente(models.Model):
    """Ambiente de trabalho (grupo infoAmb do S-2240).

    O ambiente é a unidade que o laudo descreve e à qual os fatores de risco
    se prendem. O vínculo do trabalhador com o ambiente é feito pelo contrato.
    """

    _name = "l10n_br.sst.ambiente"
    _description = "SST - Ambiente de Trabalho"
    _order = "company_id, name"

    name = fields.Char(
        string="Ambiente",
        required=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )
    local_amb = fields.Selection(
        LOCAL_AMBIENTE,
        string="Local do Ambiente",
        default="1",
        required=True,
    )
    tp_insc = fields.Selection(
        TP_INSC_ESTABELECIMENTO,
        string="Tipo de Inscrição",
        default="1",
        required=True,
    )
    nr_insc = fields.Char(
        string="Inscrição do Estabelecimento",
        size=14,
        required=True,
        help="CNPJ, CAEPF ou CNO do estabelecimento onde fica o ambiente.",
    )
    dsc_setor = fields.Char(
        string="Setor",
        required=True,
        help="Descrição do setor do ambiente, informada em dscSetor.",
    )
    descricao_atividade = fields.Text(
        string="Descrição das Atividades",
        help="Padrão da descrição das atividades desempenhadas (dscAtivDes). "
        "O contrato pode sobrescrever com a descrição do trabalhador.",
    )
    risco_ids = fields.One2many(
        "l10n_br.sst.risco",
        "ambiente_id",
        string="Fatores de Risco",
    )
    risco_count = fields.Integer(
        string="Riscos",
        compute="_compute_risco_count",
    )
    contract_ids = fields.One2many(
        "hr.contract",
        "l10n_br_sst_ambiente_id",
        string="Contratos",
    )
    active = fields.Boolean(default=True)

    @api.depends("risco_ids")
    def _compute_risco_count(self):
        for rec in self:
            rec.risco_count = len(rec.risco_ids)

    @api.constrains("nr_insc", "tp_insc")
    def _check_nr_insc(self):
        for rec in self:
            digitos = "".join(c for c in (rec.nr_insc or "") if c.isdigit())
            # CNPJ e CAEPF têm 14 dígitos; CNO tem 12.
            esperado = 12 if rec.tp_insc == "4" else 14
            if len(digitos) != esperado:
                raise ValidationError(
                    _(
                        "Ambiente %(nome)s: a inscrição do estabelecimento deve "
                        "ter %(esperado)s dígitos para o tipo informado."
                    )
                    % {"nome": rec.name, "esperado": esperado}
                )

    def _to_info_amb(self):
        """Dicionário do grupo infoAmb consumido pelo intermediário S-2240."""
        self.ensure_one()
        return {
            "local_amb": int(self.local_amb),
            "dsc_setor": self.dsc_setor,
            "tp_insc": int(self.tp_insc),
            "nr_insc": "".join(c for c in (self.nr_insc or "") if c.isdigit()),
        }

    def action_view_riscos(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "l10n_br_hr_sst.l10n_br_sst_risco_action"
        )
        action["domain"] = [("ambiente_id", "=", self.id)]
        action["context"] = {"default_ambiente_id": self.id}
        return action
