from odoo import api, fields, models


class ProjectProductEmployeeMap(models.Model):
    _inherit = "project.sale.line.employee.map"
    _order = "sequence,id"
    _sql_constraints = [
        ("uniqueness_employee", "check(1=1)", "No error"),
    ]

    product_id = fields.Many2one(
        string="Product",
        comodel_name="product.product",
    )

    sequence = fields.Integer()

    @api.depends("sale_line_id.price_unit")
    def _compute_price_unit(self):
        """override _compute_price_unit method in
        sale_timesheet/models/project_sale_line_employee_map:46
        """
        return

    def _compute_currency_id(self):
        company_currency = self.env.user.company_id.currency_id
        for line in self:
            line.currency_id = company_currency
