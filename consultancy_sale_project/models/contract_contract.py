# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ContractContract(models.Model):

    _inherit = "contract.contract"

    timesheet_report_id = fields.Many2one(
        "ir.actions.report", string="Relatório de Timesheet"
    )

    timesheet_email_aproval_template = fields.Many2one(
        "mail.template", string="Email Aprovação Timesheet"
    )

    contract_config_line_ids = fields.One2many(
        string="Contract lines",
        comodel_name="contract.line",
        inverse_name="contract_id",
        copy=True,
        context={"active_test": False},
    )
