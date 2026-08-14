# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class L10nBrHrApuracaoPeriodo(models.Model):
    """Competência de apuração de jornada.

    O fechamento é o que dá estabilidade à folha: uma vez fechado, o período
    não recalcula sozinho, e o holerite passa a ter uma referência que não muda
    debaixo dele. Reabrir é possível, mas é ato explícito e registrado.
    """

    _name = "l10n_br.hr.apuracao.periodo"
    _description = "Competência de Apuração de Jornada"
    _order = "date_from desc"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True, tracking=True)
    date_from = fields.Date(string="De", required=True, tracking=True)
    date_to = fields.Date(string="Até", required=True, tracking=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    state = fields.Selection(
        selection=[
            ("aberto", "Aberto"),
            ("apurado", "Apurado"),
            ("fechado", "Fechado"),
        ],
        default="aberto",
        required=True,
        tracking=True,
    )
    dia_ids = fields.One2many(
        comodel_name="l10n_br.hr.apuracao.dia",
        inverse_name="periodo_id",
        string="Dias apurados",
    )
    employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        string="Funcionários",
        help="Deixe vazio para apurar todos os contratos sujeitos a controle "
        "de jornada da empresa.",
    )
    dia_count = fields.Integer(compute="_compute_totais", string="Dias")
    horas_extras = fields.Float(compute="_compute_totais", digits=(8, 2))
    faltas = fields.Integer(compute="_compute_totais")
    inconsistencia_count = fields.Integer(
        compute="_compute_totais", string="Dias com inconsistência"
    )

    @api.depends("dia_ids", "dia_ids.horas_extras", "dia_ids.inconsistencia")
    def _compute_totais(self):
        for rec in self:
            dias = rec.dia_ids
            rec.dia_count = len(dias)
            rec.horas_extras = sum(dias.mapped("horas_extras"))
            rec.faltas = len(dias.filtered("falta_injustificada"))
            rec.inconsistencia_count = len(dias.filtered("inconsistencia"))

    @api.constrains("date_from", "date_to")
    def _check_datas(self):
        for rec in self:
            if rec.date_to < rec.date_from:
                raise ValidationError(
                    _("A data final da competência é anterior à inicial.")
                )

    def action_apurar(self):
        """Gera os dias do período e roda o motor (RP-09 a RP-14)."""
        for rec in self:
            if rec.state == "fechado":
                raise UserError(_("Competência fechada. Reabra antes de reapurar."))
            dias = self.env["l10n_br.hr.apuracao.dia"]._gerar_dias(
                rec.date_from,
                rec.date_to,
                employees=rec.employee_ids or None,
                company=rec.company_id,
            )
            dias.write({"periodo_id": rec.id})
            dias.apurar()
            rec.state = "apurado"
            _logger.info("Apuração %s: %d dias processados.", rec.name, len(dias))
        return True

    def _bloqueios_de_fechamento(self):
        """Motivos que impedem fechar a competência.

        Fechar com lacuna de NSR ou marcação ímpar seria transformar um
        problema conhecido em número oficial - e é esse número que vai para o
        AEJ e para o holerite.
        """
        self.ensure_one()
        bloqueios = []
        impares = self.dia_ids.filtered(lambda dia: not dia.paridade_ok)
        if impares:
            bloqueios.append(
                _("%d dia(s) com marcação sem par (número ímpar de registros).")
                % len(impares)
            )
        pendentes = self.env["l10n_br.hr.marcacao"].search_count(
            [
                ("employee_id", "=", False),
                ("date_marcacao", ">=", self.date_from),
                ("date_marcacao", "<=", self.date_to),
                ("company_id", "=", self.company_id.id),
            ]
        )
        if pendentes:
            bloqueios.append(
                _("%d marcação(ões) do período sem funcionário identificado.")
                % pendentes
            )
        if "l10n_br.hr.afd.import" in self.env:
            com_lacuna = self.env["l10n_br.hr.afd.import"].search_count(
                [
                    ("tem_lacuna", "=", True),
                    ("company_id", "=", self.company_id.id),
                    ("state", "=", "importado"),
                ]
            )
            if com_lacuna:
                bloqueios.append(
                    _(
                        "%d importação(ões) de AFD com lacuna de NSR. Lacuna é "
                        "indício de marcação suprimida e precisa ser explicada "
                        "antes do fechamento."
                    )
                    % com_lacuna
                )
        return bloqueios

    def action_fechar(self):
        """Fecha a competência, travando recálculo (RP-15)."""
        for rec in self:
            if rec.state == "fechado":
                continue
            bloqueios = rec._bloqueios_de_fechamento()
            if bloqueios and not self.env.context.get("l10n_br_forcar_fechamento"):
                raise UserError(
                    _("Não é possível fechar a competência %(nome)s:\n%(lista)s")
                    % {
                        "nome": rec.name,
                        "lista": "\n".join("- " + b for b in bloqueios),
                    }
                )
            rec.dia_ids.write({"state": "fechado"})
            rec.state = "fechado"
            rec.message_post(
                body=_("Competência fechada com %d dias apurados.") % len(rec.dia_ids)
            )
        return True

    def action_reabrir(self):
        """Reabre a competência, deixando o rastro de quem reabriu."""
        for rec in self:
            rec.dia_ids.write({"state": "apurado"})
            rec.state = "apurado"
            rec.message_post(
                body=_("Competência reaberta por %s.") % self.env.user.name
            )
        return True

    def action_ver_dias(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Dias apurados"),
            "res_model": "l10n_br.hr.apuracao.dia",
            "view_mode": "tree,form",
            "domain": [("periodo_id", "=", self.id)],
            "context": {"search_default_group_employee": 1},
        }

    @api.model
    def _periodo_da_data(self, company, data):
        """Competência fechada que contém a data, se houver."""
        return self.search(
            [
                ("company_id", "=", company.id),
                ("date_from", "<=", data),
                ("date_to", ">=", data),
            ],
            limit=1,
        )
