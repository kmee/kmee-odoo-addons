# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    l10n_br_refund_in_payslip = fields.Boolean(
        string="Reembolsar via Folha",
        help="Marque para incluir este relatório de despesas "
        "como ressarcimento na próxima folha de pagamento.",
    )
    l10n_br_payslip_id = fields.Many2one(
        comodel_name="hr.payslip",
        string="Holerite",
        readonly=True,
        help="Holerite onde esta despesa foi reembolsada.",
    )
