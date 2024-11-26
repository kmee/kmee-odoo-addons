# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMoveLine(models.Model):

    _inherit = "account.move.line"

    timesheet_invoice_workflow = fields.Selection(
        related="contract_line_id.timesheet_invoice_workflow"
    )

    timesheet_report_type = fields.Selection(
        related="contract_line_id.timesheet_report_type"
    )

    timesheet_report_detais = fields.Selection(
        related="contract_line_id.timesheet_report_detais"
    )

    timesheet_report_id = fields.Many2one(
        related="contract_line_id.contract_id.timesheet_report_id"
    )

    timesheet_email_aproval_template = fields.Many2one(
        related="contract_line_id.contract_id.timesheet_email_aproval_template"
    )
