from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"

    substitute_product_ids = fields.Many2many(
        comodel_name="product.product",
        string="Alternative Products",
        help="Products that can be used instead of the component of this line.",
    )

    @api.constrains("product_id", "substitute_product_ids")
    def _check_substitute_product_ids(self):
        for line in self:
            if line.product_id in line.substitute_product_ids:
                raise ValidationError(
                    _(
                        "The component %s cannot be an alternative of its own line.",
                        line.product_id.display_name,
                    )
                )
            category = line.product_id.uom_id.category_id
            wrong = line.substitute_product_ids.filtered(
                lambda p, category=category: p.uom_id.category_id != category
            )
            if wrong:
                raise ValidationError(
                    _(
                        "The alternative products %(products)s must use a unit of "
                        "measure of the same category as %(component)s.",
                        products=", ".join(wrong.mapped("display_name")),
                        component=line.product_id.display_name,
                    )
                )
