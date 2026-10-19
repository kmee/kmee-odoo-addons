# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    l10n_br_sst_epi_ids = fields.One2many(
        "hr.personal.equipment",
        "employee_id",
        string="EPIs",
    )
    l10n_br_sst_epi_count = fields.Integer(
        string="EPIs Válidos",
        compute="_compute_l10n_br_sst_epi_count",
    )

    @api.depends("l10n_br_sst_epi_ids.state")
    def _compute_l10n_br_sst_epi_count(self):
        for rec in self:
            rec.l10n_br_sst_epi_count = len(
                rec.l10n_br_sst_epi_ids.filtered(lambda e: e.state == "valid")
            )

    def _l10n_br_sst_epis_do_risco(self, risco, data=None):
        """Entregas válidas de EPI que neutralizam o risco na data.

        É o que alimenta o grupo ``epcEpi`` do S-2240: sem entrega válida de um
        EPI ligado ao risco, o evento não pode declarar utilização de EPI.
        """
        self.ensure_one()
        data = fields.Date.to_date(data) or fields.Date.context_today(self)
        entregas = self.l10n_br_sst_epi_ids._l10n_br_sst_valida_em(data)
        return entregas.filtered(lambda e: risco in e.l10n_br_sst_risco_ids)

    def action_l10n_br_sst_ficha_epi(self):
        """Abre a ficha de EPI do trabalhador em PDF."""
        self.ensure_one()
        return self.env.ref("l10n_br_hr_sst_epi.action_report_ficha_epi").report_action(
            self
        )

    def action_view_l10n_br_sst_epi(self):
        self.ensure_one()
        return {
            "name": _("EPIs"),
            "type": "ir.actions.act_window",
            "res_model": "hr.personal.equipment",
            "view_mode": "tree,form",
            "domain": [("employee_id", "=", self.id)],
        }
