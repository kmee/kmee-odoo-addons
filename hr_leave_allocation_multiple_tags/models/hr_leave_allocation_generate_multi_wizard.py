# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrLeaveAllocationGenerateMultiWizard(models.TransientModel):
    _inherit = "hr.leave.allocation.generate.multi.wizard"

    allocation_mode = fields.Selection(
        selection_add=[
            ("category_and", "By all Employee Tags (AND)"),
            ("category_or", "By any of Employee Tags (OR)"),
        ],
        ondelete={
            "category_and": "set default",
            "category_or": "set default",
        },
    )
    category_ids = fields.Many2many(
        "hr.employee.category",
        relation="hr_leave_alloc_multi_wizard_category_rel",
        column1="wizard_id",
        column2="category_id",
        string="Employee Tags",
    )

    def _get_employees_from_allocation_mode(self):
        self.ensure_one()
        if self.allocation_mode not in ("category_and", "category_or"):
            return super()._get_employees_from_allocation_mode()
        employees = self.env["hr.employee"].search(
            [("company_id", "in", self.env.companies.ids)]
        )
        if self.allocation_mode == "category_and":
            for category in self.category_ids:
                employees = employees.filtered(lambda e, c=category: c in e.category_ids)
        else:
            employees = employees.filtered(
                lambda e: e.category_ids & self.category_ids
            )
        return employees
