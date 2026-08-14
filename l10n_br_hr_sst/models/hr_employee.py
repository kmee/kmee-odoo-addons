# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    l10n_br_sst_ambiente_id = fields.Many2one(
        "l10n_br.sst.ambiente",
        string="Ambiente de Trabalho",
        related="contract_id.l10n_br_sst_ambiente_id",
        readonly=True,
    )

    def _l10n_br_sst_riscos_vigentes(self, data=None):
        """Riscos vigentes do contrato ativo do empregado."""
        self.ensure_one()
        if not self.contract_id:
            return self.env["l10n_br.sst.risco"]
        return self.contract_id._l10n_br_sst_riscos_vigentes(data)
