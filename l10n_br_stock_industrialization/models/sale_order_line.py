from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    applied_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Produto aplicado",
        help="Produto cobrado na rota Apenas cobrança: o item da nota é o "
        "produto aplicado e não há movimentação de estoque.",
    )

    @api.onchange("applied_product_id")
    def _onchange_applied_product_id(self):
        self.product_id = self.applied_product_id

    @api.constrains("route_id")
    def _check_billing_only_route(self):
        route = self.env.ref(
            "l10n_br_stock_industrialization.route_apenas_cobranca",
            raise_if_not_found=False,
        )
        for line in self.filtered(lambda line: route and line.route_id == route):
            if line.order_id.fiscal_operation_id not in (
                line.order_id._billing_only_operations()
            ):
                raise ValidationError(
                    self.env._(
                        "A rota Apenas cobrança só pode ser usada quando a "
                        "operação fiscal do pedido é Serviço de industrialização "
                        "ou Serviço de industrialização por conta e ordem."
                    )
                )
