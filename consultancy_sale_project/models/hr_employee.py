from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    product_line_ids = fields.One2many(
        comodel_name="hr.employee.product.line",
        inverse_name="employee_id",
    )
