from odoo import fields, models


class HrEmployeeProductLine(models.Model):
    _name = "hr.employee.product.line"

    product_tmpl_id = fields.Many2one(
        string="Produto",
        comodel_name="product.template",
    )

    list_price = fields.Float(string="Unit Price", related="product_tmpl_id.list_price")

    employee_id = fields.Many2one(
        string="Employee",
        comodel_name="hr.employee",
    )
