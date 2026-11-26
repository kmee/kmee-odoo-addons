from collections import defaultdict

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class StockReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    @api.model
    def _get_component_production(self, stock_move):
        """Manufacturing order fed by a component picking move, if it uses the
        component return."""
        production = stock_move.move_dest_ids.raw_material_production_id[:1]
        if (
            production.component_return_enabled
            and stock_move.picking_type_id
            == production.picking_type_id.warehouse_id.pbm_type_id
        ):
            return production
        return self.env["mrp.production"]

    @api.model
    def _prepare_stock_return_picking_line_vals_from_move(self, stock_move):
        vals = super()._prepare_stock_return_picking_line_vals_from_move(stock_move)
        production = self._get_component_production(stock_move)
        if production:
            vals["quantity"] = production._component_returnable_qty_for_move(stock_move)
        return vals

    def _check_component_return_quantities(self):
        totals = defaultdict(float)
        for line in self.product_return_moves.filtered("quantity"):
            production = self._get_component_production(line.move_id)
            if not production:
                continue
            allowed = production._component_returnable_qty_for_move(line.move_id)
            quantity = line.uom_id._compute_quantity(
                line.quantity, line.product_id.uom_id
            )
            totals[production, line.product_id] += quantity
            left = production._component_return_quantities().get(
                line.product_id, {"returnable": 0.0}
            )
            if (
                float_compare(
                    quantity, allowed, precision_rounding=line.uom_id.rounding
                )
                > 0
                or float_compare(
                    totals[production, line.product_id],
                    left["returnable"],
                    precision_rounding=line.uom_id.rounding,
                )
                > 0
            ):
                raise UserError(
                    _(
                        "You can only return what was not consumed by the"
                        " manufacturing order: %(product)s has %(qty)s left.",
                        product=line.product_id.display_name,
                        qty=left["returnable"],
                    )
                )

    def _create_return(self):
        self._check_component_return_quantities()
        return super()._create_return()
