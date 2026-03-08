# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

from odoo.addons.l10n_br_hr_payroll.models.salary_rules_br import calc_ferias_dias


class HrLeaveAllocation(models.Model):
    _inherit = "hr.leave.allocation"

    l10n_br_faltas_periodo_aquisitivo = fields.Integer(
        string="Faltas no Período Aquisitivo",
        default=0,
        help="Faltas injustificadas no período aquisitivo (CLT art. 130)",
    )

    @api.depends("l10n_br_faltas_periodo_aquisitivo")
    def _compute_from_holiday_status_id(self):
        """Extend to compute vacation days based on absences (CLT art. 130)."""
        super()._compute_from_holiday_status_id()
        vacation_type = self.env.ref(
            "l10n_br_hr_vacation.leave_type_ferias", raise_if_not_found=False
        )
        if not vacation_type:
            return
        for alloc in self:
            if alloc.holiday_status_id == vacation_type:
                dias = calc_ferias_dias(alloc.l10n_br_faltas_periodo_aquisitivo)
                # SQL constraint requires number_of_days > 0 for regular allocs.
                # When employee loses vacation right (33+ faltas), we keep 1 day
                # to satisfy the constraint; the field value signals the loss.
                alloc.number_of_days = max(dias, 1) if dias == 0 else dias
