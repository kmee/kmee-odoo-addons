# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrPayslipRun(models.Model):
    _inherit = "hr.payslip.run"

    # Mesmo motivo do hr.payslip: o lote de folha deve nascer no diário FOPAG,
    # que é o único configurado para contabilizar folha (ver
    # account_journal._l10n_br_payroll_journal).
    journal_id = fields.Many2one(
        default=lambda self: self.env["account.journal"]._l10n_br_payroll_journal()
    )
