from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    employee_line_ids = fields.Many2many(
        comodel_name="hr.employee",
        relation="employee_product_rel",
        column1="product_id",
        column2="employee_id",
        string="Employees",
    )
