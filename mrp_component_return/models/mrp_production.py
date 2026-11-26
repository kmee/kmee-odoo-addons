from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    component_return_enabled = fields.Boolean(
        related="picking_type_id.warehouse_id.component_return_enabled",
    )
    has_forced_return = fields.Boolean(
        string="Forced Return",
        copy=False,
        readonly=True,
        help="All the components left in pre-production were returned to stock"
        " with the 'Return All' button.",
    )
    has_pending_component_return = fields.Boolean(
        string="Pending Reservations",
        compute="_compute_has_pending_component_return",
        store=True,
        help="Components picked for this order are still in pre-production,"
        " neither consumed nor returned to stock.",
    )

    def _get_component_pickings(self):
        """Done component pickings (stock to pre-production) of the order."""
        self.ensure_one()
        pbm_type = self.picking_type_id.warehouse_id.pbm_type_id
        return self.move_raw_ids.move_orig_ids.filtered(
            lambda m: m.picking_type_id == pbm_type
        ).picking_id

    def _get_component_return_pickings(self):
        self.ensure_one()
        return self.env["stock.picking"].search(
            [("return_id", "in", self._get_component_pickings().ids)]
        )

    def _component_return_quantities(self, reserved_is_consumed=False):
        """Per product, in the product unit: ``pending`` is what was moved to
        pre-production and neither consumed nor returned (done); ``returnable``
        also discounts the returns still open. With ``reserved_is_consumed``
        the reserved quantity counts as consumed when nothing was marked as
        picked, as it is when the order is finished."""
        self.ensure_one()
        consume_reserved = reserved_is_consumed and not any(
            self.move_raw_ids.mapped("picked")
        )
        result = defaultdict(lambda: {"pending": 0.0, "returnable": 0.0})
        sent_moves = self.move_raw_ids.move_orig_ids.filtered(
            lambda m: m.state == "done"
            and m.picking_type_id == self.picking_type_id.warehouse_id.pbm_type_id
        )
        for move in sent_moves:
            result[move.product_id]["pending"] += move.product_qty
            result[move.product_id]["returnable"] += move.product_qty
        for move in sent_moves.returned_move_ids.filtered(
            lambda m: m.state != "cancel"
        ):
            result[move.product_id]["returnable"] -= move.product_qty
            if move.state == "done":
                result[move.product_id]["pending"] -= move.product_qty
        # the earlier orders of a backorder chain consumed part of what was sent
        earlier = self.procurement_group_id.mrp_production_ids.filtered(
            lambda mo: mo.backorder_sequence < self.backorder_sequence
            and mo.state == "done"
        )
        for move in (self.move_raw_ids | earlier.move_raw_ids).filtered(
            lambda m: m.state != "cancel"
        ):
            if move.state == "done" or consume_reserved:
                qty = move.quantity
            else:
                qty = sum(move.move_line_ids.filtered("picked").mapped("quantity"))
            qty = move.product_uom._compute_quantity(qty, move.product_id.uom_id)
            if move.product_id in result:
                result[move.product_id]["pending"] -= qty
                result[move.product_id]["returnable"] -= qty
        return {
            product: {key: max(value, 0.0) for key, value in values.items()}
            for product, values in result.items()
        }

    def _component_returnable_qty_for_move(self, move):
        """Quantity of a component picking move that can still be returned."""
        self.ensure_one()
        already_returned = sum(
            move.returned_move_ids.filtered(lambda m: m.state != "cancel").mapped(
                "product_qty"
            )
        )
        left = self._component_return_quantities().get(move.product_id, {})
        return max(
            min(move.product_qty - already_returned, left.get("returnable", 0.0)), 0.0
        )

    def _has_component_backorder(self):
        """The balance of the components goes on to the backorder."""
        self.ensure_one()
        return bool(
            self.procurement_group_id.mrp_production_ids.filtered(
                lambda mo: mo.backorder_sequence > self.backorder_sequence
                and mo.state != "cancel"
            )
        )

    def _get_pending_component_products(self, reserved_is_consumed=False):
        self.ensure_one()
        if self._has_component_backorder():
            return self.env["product.product"]
        quantities = self._component_return_quantities(reserved_is_consumed)
        return self.env["product.product"].browse(
            [
                product.id
                for product, qty in quantities.items()
                if not float_is_zero(
                    qty["pending"], precision_rounding=product.uom_id.rounding
                )
            ]
        )

    @api.depends(
        "component_return_enabled",
        "move_raw_ids.state",
        "move_raw_ids.picked",
        "move_raw_ids.quantity",
        "move_raw_ids.move_line_ids.picked",
        "move_raw_ids.move_orig_ids.state",
        "move_raw_ids.move_orig_ids.returned_move_ids.state",
    )
    def _compute_has_pending_component_return(self):
        for production in self:
            production.has_pending_component_return = bool(
                production.component_return_enabled
                and production._get_pending_component_products()
            )

    def _check_component_return_before_cancel(self):
        self.ensure_one()
        if self.workorder_ids.filtered(lambda wo: wo.state not in ("done", "cancel")):
            raise UserError(
                _(
                    "%s cannot be cancelled while it has open work orders.",
                    self.display_name,
                )
            )
        if self._get_component_return_pickings().filtered(
            lambda p: p.state not in ("done", "cancel")
        ):
            raise UserError(
                _(
                    "%s cannot be cancelled while it has an open component return."
                    " Validate or cancel the return first.",
                    self.display_name,
                )
            )
        products = self._get_pending_component_products()
        if products:
            raise UserError(
                _(
                    "%(order)s cannot be cancelled: the components below were picked"
                    " and are still in pre-production. Use 'Return All' to send"
                    " them back to stock.\n%(products)s",
                    order=self.display_name,
                    products="\n".join(products.mapped("display_name")),
                )
            )

    def action_cancel(self):
        for production in self.filtered("component_return_enabled"):
            production._check_component_return_before_cancel()
        return super().action_cancel()

    def button_mark_done(self):
        for production in self.filtered("component_return_enabled"):
            rounding = production.product_uom_id.rounding
            partial = (
                float_compare(production.qty_producing, 0, precision_rounding=rounding)
                > 0
                and float_compare(
                    production.qty_producing,
                    production.product_qty,
                    precision_rounding=rounding,
                )
                < 0
            )
            if partial:
                continue
            products = production._get_pending_component_products(
                reserved_is_consumed=True
            )
            if products:
                raise UserError(
                    _(
                        "%(order)s cannot be done: the components below were picked"
                        " and neither consumed nor returned to stock. Consume them or"
                        " use 'Return All' and validate the return.\n%(products)s",
                        order=production.display_name,
                        products="\n".join(products.mapped("display_name")),
                    )
                )
        return super().button_mark_done()

    def _return_picking_action(self, pickings):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "stock.action_picking_tree_all"
        )
        action["domain"] = [("id", "in", pickings.ids)]
        if len(pickings) == 1:
            action["views"] = [(False, "form")]
            action["res_id"] = pickings.id
        return action

    def button_force_return_all(self):
        """Return to stock everything that is still in pre-production."""
        self.ensure_one()
        created = self.env["stock.picking"]
        for picking in self._get_component_pickings().filtered(
            lambda p: p.state == "done"
        ):
            wizard = (
                self.env["stock.return.picking"]
                .with_context(
                    active_id=picking.id,
                    active_ids=picking.ids,
                    active_model="stock.picking",
                )
                .create({"picking_id": picking.id})
            )
            if not wizard.product_return_moves.filtered("quantity"):
                continue
            new_picking = wizard._create_return()
            new_picking.is_final_mo_return = True
            created |= new_picking
        if not created:
            raise UserError(_("There is nothing left to return to stock."))
        self.has_forced_return = True
        return self._return_picking_action(created)

    def action_resolve_component_return(self):
        """Open the return of the components still in pre-production."""
        self.ensure_one()
        pickings = self._get_component_pickings().filtered(
            lambda p: p.state == "done"
            and any(self._component_returnable_qty_for_move(m) for m in p.move_ids)
        )
        if not pickings:
            open_returns = self._get_component_return_pickings().filtered(
                lambda p: p.state not in ("done", "cancel")
            )
            if open_returns:
                return self._return_picking_action(open_returns)
            raise UserError(_("There is nothing left to return to stock."))
        if len(pickings) > 1:
            return self._return_picking_action(pickings)
        action = self.env["ir.actions.actions"]._for_xml_id(
            "stock.act_stock_return_picking"
        )
        action["context"] = {
            "active_id": pickings.id,
            "active_ids": pickings.ids,
            "active_model": "stock.picking",
        }
        return action
