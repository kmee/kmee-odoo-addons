# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    l10n_br_expense_sheet_ids = fields.One2many(
        comodel_name="hr.expense.sheet",
        inverse_name="l10n_br_payslip_id",
        string="Despesas Reembolsadas",
        readonly=True,
    )
    l10n_br_expenses_count = fields.Integer(
        string="Despesas",
        compute="_compute_l10n_br_expenses_count",
    )
    l10n_br_total_ressarcimento = fields.Float(
        string="Total Ressarcimento",
        compute="_compute_l10n_br_total_ressarcimento",
    )

    @api.depends("l10n_br_expense_sheet_ids")
    def _compute_l10n_br_expenses_count(self):
        for rec in self:
            rec.l10n_br_expenses_count = len(rec.l10n_br_expense_sheet_ids)

    @api.depends("l10n_br_expense_sheet_ids")
    def _compute_l10n_br_total_ressarcimento(self):
        for rec in self:
            total = 0.0
            for sheet in rec.l10n_br_expense_sheet_ids:
                for expense in sheet.expense_line_ids:
                    total += expense.unit_amount * expense.quantity
            rec.l10n_br_total_ressarcimento = total

    def action_link_pending_expenses(self):
        """Link approved expense sheets flagged for payslip reimbursement."""
        for rec in self:
            sheets = self.env["hr.expense.sheet"].search(
                [
                    ("employee_id", "=", rec.employee_id.id),
                    ("l10n_br_refund_in_payslip", "=", True),
                    ("l10n_br_payslip_id", "=", False),
                    ("state", "in", ("approve", "post", "done")),
                ]
            )
            sheets.write({"l10n_br_payslip_id": rec.id})

    def compute_sheet(self):
        """Link pending expenses BEFORE computing payslip.

        Expenses must be linked first so the RESSARCIMENTO salary rule
        can read l10n_br_total_ressarcimento during rule evaluation.
        """
        self.action_link_pending_expenses()
        self.invalidate_recordset(
            ["l10n_br_expense_sheet_ids", "l10n_br_total_ressarcimento"]
        )
        return super().compute_sheet()

    def _get_baselocaldict(self, contracts):
        """Pre-populate RESSARCIMENTO with 0.0 default."""
        localdict = super()._get_baselocaldict(contracts)
        localdict.setdefault("RESSARCIMENTO", 0.0)
        return localdict
