from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    product_line_ids = fields.Many2many(
        comodel_name="product.template",
        relation="employee_product_rel",
        column1="employee_id",
        column2="product_id",
        string="Products",
    )
