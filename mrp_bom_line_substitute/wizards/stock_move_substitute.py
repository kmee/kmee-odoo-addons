from odoo import api, fields, models
from odoo.tools import float_compare


class StockMoveSubstitute(models.TransientModel):
    _name = "stock.move.substitute"
    _description = "Replace a component by an alternative product"

    move_id = fields.Many2one("stock.move", required=True, readonly=True)
    original_product_id = fields.Many2one(related="move_id.product_id")
    substitute_product_ids = fields.Many2many(
        related="move_id.substitute_product_ids",
    )
    product_id = fields.Many2one(
        "product.product",
        string="Alternative Product",
        required=True,
        domain="[('id', 'in', substitute_product_ids)]",
    )
    product_uom_id = fields.Many2one(related="move_id.product_uom")
    product_uom_qty = fields.Float(
        string="Quantity to Replace",
        digits="Product Unit of Measure",
        required=True,
        compute="_compute_product_uom_qty",
        store=True,
        readonly=False,
    )
    available_qty = fields.Float(
        string="Alternative Available",
        compute="_compute_available_qty",
        digits="Product Unit of Measure",
    )

    @api.depends("move_id")
    def _compute_product_uom_qty(self):
        for wizard in self:
            move = wizard.move_id
            missing = move.product_uom_qty - move.quantity
            rounding = move.product_uom.rounding
            wizard.product_uom_qty = (
                missing
                if float_compare(missing, 0, precision_rounding=rounding) > 0
                else move.product_uom_qty
            )

    @api.depends("product_id", "move_id")
    def _compute_available_qty(self):
        for wizard in self:
            wizard.available_qty = wizard.product_id.with_context(
                location=wizard.move_id.location_id.id
            ).free_qty

    def action_confirm(self):
        self.ensure_one()
        self.move_id._substitute_component(self.product_id, self.product_uom_qty)
        return {"type": "ir.actions.act_window_close"}
