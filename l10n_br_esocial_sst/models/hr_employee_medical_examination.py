# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class HrEmployeeMedicalExamination(models.Model):
    """Liga o ASO concluído ao evento S-2220."""

    _inherit = "hr.employee.medical.examination"

    l10n_br_s2220_id = fields.Many2one(
        "l10n_br.esocial.s2220",
        string="Evento S-2220",
        readonly=True,
        copy=False,
    )
    l10n_br_esocial_state = fields.Selection(
        related="l10n_br_s2220_id.evento_id.state",
        string="Situação no eSocial",
        readonly=True,
    )

    def action_gerar_s2220(self):
        """Cria o intermediário do S-2220 deste ASO."""
        self.ensure_one()
        evento = self.env["l10n_br.esocial.s2220"].gerar_para_exame(self)
        self.l10n_br_s2220_id = evento
        return {
            "name": _("S-2220"),
            "type": "ir.actions.act_window",
            "res_model": "l10n_br.esocial.s2220",
            "view_mode": "form",
            "res_id": evento.id,
        }

    def to_done(self):
        """Concluir o ASO já deixa o evento do eSocial preparado."""
        res = super().to_done()
        for rec in self:
            if not rec.l10n_br_s2220_id:
                rec.l10n_br_s2220_id = self.env[
                    "l10n_br.esocial.s2220"
                ].gerar_para_exame(rec)
        return res
