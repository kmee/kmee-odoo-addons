# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ESocialS1298(models.Model):
    _name = "l10n_br.esocial.s1298"
    _inherit = "l10n_br.esocial.base.intermediario"
    _description = "eSocial S-1298 - Reabertura dos Eventos Periódicos"
    _order = "per_apur desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    per_apur = fields.Char(
        string="Período Apuração",
        size=7,
        required=True,
        help="AAAA-MM para a folha mensal, AAAA para o 13º salário.",
    )
    ind_apuracao = fields.Selection(
        [
            ("1", "Mensal"),
            ("2", "Anual (13º Salário)"),
        ],
        string="Tipo Apuração",
        default="1",
        required=True,
    )
    fechamento_evento_id = fields.Many2one(
        "l10n_br.esocial.evento",
        string="Fechamento a Reabrir",
        compute="_compute_fechamento_evento_id",
        help="S-1299 aceito que esta reabertura desfaz.",
    )

    @api.depends("per_apur")
    def _compute_name(self):
        for rec in self:
            rec.name = f"S-1298 {rec.per_apur or ''}".strip()

    @api.depends("per_apur", "company_id")
    def _compute_fechamento_evento_id(self):
        eventos = self.env["l10n_br.esocial.evento"]
        for rec in self:
            if not rec.per_apur or not rec.company_id:
                rec.fechamento_evento_id = eventos
                continue
            rec.fechamento_evento_id = eventos.search(
                [
                    ("company_id", "=", rec.company_id.id),
                    ("per_apur", "=", rec.per_apur),
                    ("tipo", "=", "S-1299"),
                    ("state", "=", "success"),
                ],
                order="id desc",
                limit=1,
            )

    @api.constrains("per_apur", "ind_apuracao")
    def _check_per_apur(self):
        for rec in self:
            rec._validar_competencia(
                rec.per_apur, _("Período Apuração"), anual=rec.ind_apuracao == "2"
            )

    def _get_event_type(self):
        return "S-1298"

    def _prepare_evento_vals(self, xml, id_evento):
        vals = super()._prepare_evento_vals(xml, id_evento)
        vals["per_apur"] = self.per_apur
        return vals

    def action_gerar_evento(self):
        """Só reabre competência efetivamente fechada."""
        self.ensure_one()
        if not self.fechamento_evento_id:
            raise UserError(
                _(
                    "A competência %(per)s não possui fechamento (S-1299) "
                    "aceito, então não há o que reabrir."
                )
                % {"per": self.per_apur}
            )
        return super().action_gerar_evento()

    def _to_esociallib_dict(self):
        self.ensure_one()
        ide = self._get_ide_empregador()
        proc = self._get_proc_info()
        return {
            "tp_insc": ide["tp_insc"],
            "nr_insc": ide["nr_insc"],
            "ind_apuracao": int(self.ind_apuracao),
            "per_apur": self.per_apur,
            "proc_emi": proc["proc_emi"],
            "ver_proc": proc["ver_proc"],
        }
