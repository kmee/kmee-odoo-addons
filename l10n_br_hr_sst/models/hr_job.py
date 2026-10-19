# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HrJob(models.Model):
    _inherit = "hr.job"

    l10n_br_sst_risco_ids = fields.Many2many(
        "l10n_br.sst.risco",
        relation="l10n_br_sst_risco_hr_job_rel",
        column1="job_id",
        column2="risco_id",
        string="Riscos da Função",
        help="Riscos cadastrados especificamente para esta função. Riscos de "
        "ambiente sem função listada também atingem quem trabalha nele.",
    )
    l10n_br_sst_risco_count = fields.Integer(
        string="Riscos",
        compute="_compute_l10n_br_sst_risco_count",
    )

    @api.depends("l10n_br_sst_risco_ids")
    def _compute_l10n_br_sst_risco_count(self):
        for rec in self:
            rec.l10n_br_sst_risco_count = len(rec.l10n_br_sst_risco_ids)
