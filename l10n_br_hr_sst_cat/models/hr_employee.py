# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    l10n_br_sst_acidente_ids = fields.One2many(
        "l10n_br.sst.acidente",
        "employee_id",
        string="Acidentes de Trabalho",
    )
    l10n_br_sst_acidente_count = fields.Integer(
        string="Acidentes",
        compute="_compute_l10n_br_sst_acidente_count",
    )

    @api.depends("l10n_br_sst_acidente_ids")
    def _compute_l10n_br_sst_acidente_count(self):
        for rec in self:
            rec.l10n_br_sst_acidente_count = len(
                rec.l10n_br_sst_acidente_ids.filtered(lambda a: a.state != "cancelled")
            )

    def action_view_l10n_br_sst_acidente(self):
        self.ensure_one()
        return {
            "name": _("Acidentes de Trabalho"),
            "type": "ir.actions.act_window",
            "res_model": "l10n_br.sst.acidente",
            "view_mode": "tree,form",
            "domain": [("employee_id", "=", self.id)],
            "context": {"default_employee_id": self.id},
        }
