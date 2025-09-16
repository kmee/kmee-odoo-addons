# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo import _, api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    original_bo_qty = fields.Float(
        string="B.O. Original Qty",
        readonly=True,
    )

    available_bo_qty = fields.Float(
        string="B.O. Available Qty",
        compute="_compute_bo_quantities",
    )

    blanket_order_line_id = fields.Many2one(
        comodel_name="sale.blanket.order.line",
        string="Blanket Order Line",
        copy=False,
    )

    # @api.onchange("product_id", "order_partner_id")
    # def onchange_product_id(self):
    #     return

    # @api.onchange("product_uom", "product_uom_qty")
    def product_uom_change(self):
        return

    @api.depends("blanket_order_line_id", "product_uom_qty")
    def _compute_bo_quantities(self):
        for line in self:
            if line.blanket_order_line_id:
                line.original_bo_qty = line.blanket_order_line_id.original_uom_qty
                line.available_bo_qty = line.blanket_order_line_id.remaining_qty
            else:
                line.original_bo_qty = 0.0
                line.available_bo_qty = 0.0

    @api.onchange("product_id", "order_id.blanket_order_id")
    def _onchange_product_blanket_order(self):
        if self.order_id.blanket_order_id and self.product_id:
            bo_line = self.order_id.blanket_order_id.line_ids.filtered(
                lambda line_item: line_item.product_id == self.product_id
            )
            if bo_line:
                self.blanket_order_line_id = bo_line[0].id
                self.product_uom = bo_line[0].product_uom.id
                self.price_unit = bo_line[0].price_unit
                # Propagate discount from Blanket Order line if available
                if hasattr(bo_line[0], "discount"):
                    self.discount = bo_line[0].discount

    @api.onchange("product_uom_qty", "blanket_order_line_id")
    def _onchange_qty_blanket_order(self):
        if self.order_id.blanket_order_type == "reference":
            if (
                self.blanket_order_line_id
                and self.product_uom_qty > self.available_bo_qty
            ):
                return {
                    "warning": {
                        "title": _("Warning"),
                        "message": _(
                            "Requested quantity %(qty)s exceeds available balance %(balance)s"
                        )
                        % {
                            "qty": self.product_uom_qty,
                            "balance": self.available_bo_qty,
                        },
                    }
                }

    def create_blanket_order_line(self):
        bo_line = self.env["sale.blanket.order.line"].create(
            self._prepare_sale_order_line_values()
        )
        blanket_order_id = self.order_id.blanket_order_id.id
        self.env["sale.blanket.order"].browse(blanket_order_id).write(
            {
                "line_ids": [(4, bo_line.id)],
            }
        )

    def _prepare_sale_order_line_values(self):
        """Prepare values for creating blanket order line from sale order line."""
        return {
            "product_id": self.product_id.id,
            "name": self.name,
            "product_uom": self.product_uom.id,
            "price_unit": self.price_unit,
            "discount": self.discount,
            "original_uom_qty": self.product_uom_qty,
            "order_id": self.order_id.blanket_order_id.id,
        }
