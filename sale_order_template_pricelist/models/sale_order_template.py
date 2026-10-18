from odoo import fields, models


class SaleOrderTemplate(models.Model):
    _inherit = "sale.order.template"

    pricelist_id = fields.Many2one(
        comodel_name="product.pricelist",
        string="Pricelist",
        help="This pricelist will be applied to the sale order when this template is selected.",
    )
