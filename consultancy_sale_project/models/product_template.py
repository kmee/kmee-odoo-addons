from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    employee_line_ids = fields.Many2many(
        string="Employees",
        comodel_name="hr.employee",
    )
