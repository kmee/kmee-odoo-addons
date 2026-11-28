from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero


class StockMove(models.Model):
    _inherit = "stock.move"

    substitute_product_ids = fields.Many2many(
        comodel_name="product.product",
        string="Alternative Products",
        compute="_compute_substitute_product_ids",
        store=True,
        readonly=False,
    )
    is_substitute = fields.Boolean(string="Is Alternative Product", copy=False)
    has_been_replaced = fields.Boolean(copy=False)
    to_replace = fields.Boolean(
        string="Needs Replacement",
        copy=False,
        help="Marks a component whose replacement by an alternative is pending.",
    )
    lot_id = fields.Many2one(
        comodel_name="stock.lot",
        string="Lot/Serial Number",
        index="btree_not_null",
        copy=False,
        help="Lot of the alternative product that replaced the component.",
    )
    substitute_line_ids = fields.Many2many(
        comodel_name="stock.move",
        relation="stock_move_stock_move_relation",
        column1="original_product",
        column2="substitute_product",
        string="Replacement Moves",
        copy=False,
    )
    original_move_line_ids = fields.Many2many(
        comodel_name="stock.move",
        relation="stock_move_stock_move_original_relation",
        column1="substitute_product",
        column2="original_product",
        string="Replaced Moves",
        copy=False,
    )

    @api.depends("bom_line_id", "move_dest_ids", "move_dest_ids.substitute_product_ids")
    def _compute_substitute_product_ids(self):
        for move in self:
            if move.is_substitute:
                move.substitute_product_ids = False
            elif move.raw_material_production_id:
                move.substitute_product_ids = move.bom_line_id.substitute_product_ids
            else:
                raw = move.move_dest_ids.filtered("raw_material_production_id")[:1]
                move.substitute_product_ids = raw.substitute_product_ids

    def _get_substitutable_raw_move(self):
        """Return the manufacturing order component move fed by this move."""
        self.ensure_one()
        return self.move_dest_ids.filtered(
            lambda m: m.raw_material_production_id
            and m.product_id == self.product_id
            and m.state not in ("done", "cancel")
        )[:1]

    def action_open_substitute_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Replace Component"),
            "res_model": "stock.move.substitute",
            "view_mode": "form",
            "target": "new",
            "context": {"default_move_id": self.id},
        }

    def _substitute_component(self, product, qty):
        """Replace ``qty`` of this component move by ``product``.

        Works on the component move of the picking that supplies a
        manufacturing order. The picking and the order lose ``qty`` of the
        original component and gain a move of the alternative product.
        """
        self.ensure_one()
        raw = self._get_substitutable_raw_move()
        if self.raw_material_production_id or not raw:
            raise UserError(
                _("The move of %s does not supply a manufacturing order.")
                % self.product_id.display_name
            )
        if self.state in ("done", "cancel", "draft"):
            raise UserError(_("Only confirmed moves can be replaced."))
        if product not in raw.substitute_product_ids:
            raise UserError(
                _("%(product)s is not an alternative of %(component)s.")
                % {
                    "product": product.display_name,
                    "component": self.product_id.display_name,
                }
            )
        rounding = self.product_uom.rounding
        if float_compare(qty, 0, precision_rounding=rounding) <= 0 or (
            float_compare(qty, self.product_uom_qty, precision_rounding=rounding) > 0
        ):
            raise UserError(
                _("The quantity must be between zero and the demand of the move.")
            )
        raw_qty = self.product_uom._compute_quantity(qty, raw.product_uom)
        if (
            float_compare(
                raw_qty,
                raw.product_uom_qty,
                precision_rounding=raw.product_uom.rounding,
            )
            > 0
        ):
            raise UserError(_("The manufacturing order needs less than that."))

        new_demand = self.product_uom_qty - qty
        if float_compare(self.quantity, new_demand, precision_rounding=rounding) > 0:
            self._do_unreserve()

        new_pick = self.copy(
            {
                "product_id": product.id,
                "product_uom_qty": qty,
                "is_substitute": True,
                "original_move_line_ids": [(6, 0, self.ids)],
                "picking_id": self.picking_id.id,
            }
        )
        new_raw = raw.copy(
            {
                "product_id": product.id,
                "product_uom_qty": raw_qty,
                "bom_line_id": False,
                "is_substitute": True,
                "original_move_line_ids": [(6, 0, raw.ids)],
                "move_orig_ids": [(6, 0, new_pick.ids)],
            }
        )
        (self | raw).has_been_replaced = True
        self.substitute_line_ids |= new_pick
        raw.substitute_line_ids |= new_raw

        self._reduce_or_cancel(qty, "move_dest_ids", raw)
        raw._reduce_or_cancel(raw_qty, "move_orig_ids", self)

        (new_pick | new_raw)._action_confirm(merge=False)
        self.picking_id.action_assign()
        new_pick.lot_id = new_pick.move_line_ids.lot_id[:1]
        new_raw.lot_id = new_pick.lot_id
        raw.to_replace = False
        return new_pick

    def _reduce_or_cancel(self, qty, link_field, linked_move):
        """Take ``qty`` from the demand; cancel the move when nothing is left.

        ``no_procurement`` keeps the core from propagating the lower demand of
        the component to the picking, which is reduced here on its own.
        """
        self.ensure_one()
        self = self.with_context(no_procurement=True)
        remaining = self.product_uom_qty - qty
        if float_is_zero(remaining, precision_rounding=self.product_uom.rounding):
            self[link_field] = [(3, linked_move.id)]
            self.product_uom_qty = 0
            self._action_cancel()
        else:
            self.product_uom_qty = remaining
