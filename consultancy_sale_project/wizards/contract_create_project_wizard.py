# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ContractCreateProjectWizard(models.TransientModel):

    _name = "contract.create.project.wizard"

    name = fields.Char()

    contract_id = fields.Many2one(
        "contract.contract",
        default=lambda self: self._context.get("active_id"),
        readonly=True,
    )

    analytic_account_id = fields.Many2one(
        "account.analytic.account",
    )

    project_template_id = fields.Many2one(
        "project.project",
    )

    default_contract_line_id = fields.Many2one(
        "contract.line",
    )

    allow_billable = fields.Boolean(default=True)
    allow_timesheets = fields.Boolean(default=True)
    allow_milestones = fields.Boolean(default=True)

    def doit(self):
        for wizard in self:

            vals = {
                "name": wizard.name,
                "partner_id": self.contract_id.partner_id.id,
                "contract_line_id": self.default_contract_line_id.id,
                "analytic_account_id": self.analytic_account_id.id,
                "allow_billable": True,
                "allow_timesheets": True,
                "allow_milestones": True,
            }

            if wizard.project_template_id:
                project = wizard.project_template_id.copy()
                project.update(vals)
            else:
                self.env["project.project"].create(vals)

        return self.contract_id.action_view_projects()
