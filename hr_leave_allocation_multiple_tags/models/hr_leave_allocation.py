# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrLeaveAllocation(models.Model):
    _inherit = "hr.leave.allocation"

    holiday_type = fields.Selection(
        selection_add=[
            ("category_and", "All Tags (AND)"),
            ("category_or", "Any of Tags (OR)"),
        ],
        ondelete={
            "category_and": "set default",
            "category_or": "set default",
        },
    )

    category_ids = fields.Many2many(
        "hr.employee.category",
        compute="_compute_from_holiday_type",
        store=True,
        string="Employee Tags",
        readonly=False,
    )

    @api.depends("holiday_type")
    def _compute_from_holiday_type(self):
        res = super()._compute_from_holiday_type()
        for allocation in self:
            if allocation.holiday_type in ["category_and", "category_or"]:
                allocation.employee_ids = False
                allocation.mode_company_id = False
        return res

    def _action_validate_create_childs(self):
        childs = (
            super()._action_validate_create_childs() or self.env["hr.leave.allocation"]
        )
        for allocation in self:
            if allocation.state != "validate" or allocation.holiday_type not in (
                "category_and",
                "category_or",
            ):
                continue
            employees = self.env["hr.employee"]
            if allocation.holiday_type == "category_and":
                employees = self.env["hr.employee"].search([])
                for category in allocation.category_ids:
                    employees = employees.filtered(lambda e: category in e.category_ids)
            else:
                for category in allocation.category_ids:
                    employees |= category.employee_ids
            if employees:
                new_childs = allocation.with_context(
                    mail_notify_force_send=False, mail_activity_automation_skip=True
                ).create(allocation._prepare_holiday_values(employees))
                new_childs.action_validate()
                childs += new_childs
        return childs

    @api.constrains(
        "holiday_type",
        "employee_id",
        "multi_employee",
        "category_id",
        "category_ids",
        "department_id",
        "mode_company_id",
    )
    def _check_type_value(self):
        for allocation in self:
            if allocation.holiday_type == "employee":
                if not allocation.employee_id and not allocation.multi_employee:
                    raise ValidationError(
                        _(
                            "The employee must be specified for 'Employee' type allocation."
                        )
                    )
            elif allocation.holiday_type == "category":
                if not allocation.category_id:
                    raise ValidationError(
                        _(
                            "The category must be specified for 'Category' type allocation."
                        )
                    )
            elif allocation.holiday_type in ["category_and", "category_or"]:
                if not allocation.category_ids:
                    raise ValidationError(
                        _(
                            """At least one employee tag must be specified for
                            'Category AND/OR' type allocation."""
                        )
                    )
            elif allocation.holiday_type == "department":
                if not allocation.department_id:
                    raise ValidationError(
                        _(
                            """The department must be specified for
                             'Department' type allocation."""
                        )
                    )
            elif allocation.holiday_type == "company":
                if not allocation.mode_company_id:
                    raise ValidationError(
                        _(
                            "The company must be specified for 'Company' type allocation."
                        )
                    )

    _sql_constraints = [
        (
            "type_value",
            "CHECK(1=1)",
            """The employee, department, company, or employee category of this request is
             missing. Please make sure that your user login is linked to an employee.""",
        ),
        (
            "duration_check",
            """CHECK( (number_of_days > 0 AND allocation_type='regular') or
             (allocation_type != 'regular'))""",
            "The duration must be greater than 0.",
        ),
    ]
