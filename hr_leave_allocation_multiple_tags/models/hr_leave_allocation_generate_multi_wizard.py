# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.fields import Domain


class HrLeaveAllocationGenerateMultiWizard(models.TransientModel):
    _inherit = "hr.leave.allocation.generate.multi.wizard"

    category_ids = fields.Many2many(
        "hr.employee.category",
        relation="hr_leave_alloc_multi_wizard_category_rel",
        column1="wizard_id",
        column2="category_id",
        string="Employee Tags",
    )
    category_mode = fields.Selection(
        selection=[
            ("any", "Any of the Employee Tags (OR)"),
            ("all", "All of the Employee Tags (AND)"),
        ],
        string="Tags Match",
        default="any",
        required=True,
    )

    def _get_employee_domain(self):
        domain = super()._get_employee_domain()
        if not self.category_ids:
            return domain
        if self.category_mode == "all":
            for category in self.category_ids:
                domain &= Domain("category_ids", "in", category.ids)
        else:
            domain &= Domain("category_ids", "in", self.category_ids.ids)
        return domain
