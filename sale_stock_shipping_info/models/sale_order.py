# Copyright (C) 2026-Today - KMEE (<http://www.kmee.com.br>).
# @author Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    shipping_weight = fields.Float(
        string="Total Weight",
        compute="_compute_shipping_info",
        store=True,
        readonly=True,
        digits="Stock Weight",
    )
    shipping_volume = fields.Float(
        string="Total Volume",
        compute="_compute_shipping_info",
        store=True,
        readonly=True,
    )
    longest_dimension = fields.Float()
    weight_uom_name = fields.Char(
        string="Weight Unit",
        compute="_compute_weight_uom_name",
        readonly=True,
    )
    volume_uom_name = fields.Char(
        string="Volume Unit",
        compute="_compute_volume_uom_name",
        readonly=True,
    )
    dimension_uom_name = fields.Char(
        string="Dimension Unit",
        compute="_compute_dimension_uom_name",
        readonly=True,
    )

    @api.depends(
        "order_line.product_id",
        "order_line.product_uom_qty",
        "order_line.product_uom",
    )
    def _compute_shipping_info(self):
        uom_meter = self.env.ref("uom.product_uom_meter", raise_if_not_found=False)
        for order in self:
            weight = 0.0
            volume = 0.0
            max_dim = 0.0
            for line in order.order_line.filtered(
                lambda l: l.product_id and not l.display_type and l.product_uom_qty > 0
            ):
                product = line.product_id
                qty_in_base_uom = line.product_uom._compute_quantity(
                    line.product_uom_qty, product.uom_id
                )
                weight += product.weight * qty_in_base_uom
                volume += product.volume * qty_in_base_uom
                if (
                    uom_meter
                    and hasattr(product, "dimensional_uom_id")
                    and product.dimensional_uom_id
                ):
                    dims = [
                        getattr(product, "product_length", 0.0) or 0.0,
                        getattr(product, "product_height", 0.0) or 0.0,
                        getattr(product, "product_width", 0.0) or 0.0,
                    ]
                    longest = max(dims)
                    if longest:
                        dim_in_m = product.dimensional_uom_id._compute_quantity(
                            longest, uom_meter
                        )
                        max_dim = max(max_dim, dim_in_m)
            order.shipping_weight = weight
            order.shipping_volume = volume

    def _compute_weight_uom_name(self):
        self.weight_uom_name = self.env[
            "product.template"
        ]._get_weight_uom_name_from_ir_config_parameter()

    def _compute_volume_uom_name(self):
        self.volume_uom_name = self.env[
            "product.template"
        ]._get_volume_uom_name_from_ir_config_parameter()

    def _compute_dimension_uom_name(self):
        uom_meter = self.env.ref("uom.product_uom_meter", raise_if_not_found=False)
        for record in self:
            record.dimension_uom_name = uom_meter.name if uom_meter else "m"
