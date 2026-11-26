# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    line_ids = fields.One2many(
        "mrp.workorder.line", "workorder_id", string="Consumed components"
    )
    is_last_wo = fields.Boolean(string="Last work order", compute="_compute_is_last_wo")
    previous_wo_produced_qty = fields.Float(
        string="Released by previous work order",
        help="Quantity already recorded by the previous work order.",
        digits="Product Unit of Measure",
        compute="_compute_previous_wo_produced_qty",
    )
    available_production_qty = fields.Float(
        string="Available to produce",
        help="Quantity that can still be recorded in this work order: limited by "
        "the previous work order, by the reserved components and by the "
        "quantity to produce.",
        digits="Product Unit of Measure",
        compute="_compute_available_production_qty",
    )
    qty_launched = fields.Float(
        string="Posted to manufacturing order",
        help="Quantity already posted to the manufacturing order.",
        digits="Product Unit of Measure",
        copy=False,
    )
    qty_to_launch = fields.Float(
        string="Quantity to post",
        help="Recorded quantity not yet posted to the manufacturing order. "
        "Only the last work order posts it.",
        digits="Product Unit of Measure",
        compute="_compute_qty_to_launch",
    )

    def _get_previous_workorders(self):
        return self.blocked_by_workorder_ids.filtered(lambda wo: wo.state != "cancel")

    @api.depends("needed_by_workorder_ids.state")
    def _compute_is_last_wo(self):
        for wo in self:
            wo.is_last_wo = not wo.needed_by_workorder_ids.filtered(
                lambda nxt: nxt.state != "cancel"
            )

    @api.depends(
        "blocked_by_workorder_ids.qty_produced", "blocked_by_workorder_ids.state"
    )
    def _compute_previous_wo_produced_qty(self):
        for wo in self:
            previous = wo._get_previous_workorders()
            wo.previous_wo_produced_qty = (
                min(previous.mapped("qty_produced")) if previous else 0.0
            )

    @api.depends(
        "qty_produced",
        "qty_remaining",
        "blocked_by_workorder_ids.qty_produced",
        "blocked_by_workorder_ids.state",
        "move_raw_ids.quantity",
        "move_raw_ids.state",
        "move_raw_ids.unit_factor",
    )
    def _compute_available_production_qty(self):
        for wo in self:
            limits = [wo.qty_produced + wo.qty_remaining]
            if wo._get_previous_workorders():
                limits.append(wo.previous_wo_produced_qty)
            for move in wo._get_component_moves():
                limits.append(move.quantity / move.unit_factor)
            wo.available_production_qty = max(min(limits) - wo.qty_produced, 0.0)

    @api.depends("qty_produced", "qty_launched", "is_last_wo")
    def _compute_qty_to_launch(self):
        for wo in self:
            wo.qty_to_launch = (
                wo.qty_produced - wo.qty_launched if wo.is_last_wo else 0.0
            )

    @api.depends("blocked_by_workorder_ids.qty_produced")
    def _compute_state(self):
        res = super()._compute_state()
        # The next work order is released as soon as the previous ones have
        # recorded some quantity, not only when they are finished.
        for wo in self:
            previous = wo._get_previous_workorders()
            if (
                wo.state == "pending"
                and wo.production_availability == "assigned"
                and all(p.state == "done" or p.qty_produced > 0 for p in previous)
            ):
                wo.state = "ready"
        return res

    def _get_component_moves(self):
        self.ensure_one()
        return self.move_raw_ids.filtered(
            lambda move: move.state not in ("done", "cancel") and move.unit_factor
        )

    def open_record_production(self):
        self.ensure_one()
        return {
            "name": _("Record production"),
            "type": "ir.actions.act_window",
            "res_model": "mrp.workorder.register.production",
            "view_mode": "form",
            "target": "new",
            "context": {"default_workorder_id": self.id},
        }

    def open_set_qty_produced(self):
        self.ensure_one()
        return {
            "name": _("Correct quantity"),
            "type": "ir.actions.act_window",
            "res_model": "mrp.workorder.set.qty.produced",
            "view_mode": "form",
            "target": "new",
            "context": {"default_workorder_id": self.id},
        }

    def record_production(self, qty):
        """Record ``qty`` as produced and the proportional component consumption."""
        self.ensure_one()
        rounding = self.product_uom_id.rounding
        if float_compare(qty, 0, precision_rounding=rounding) <= 0:
            raise UserError(_("The quantity produced must be greater than zero."))
        if (
            float_compare(
                qty, self.available_production_qty, precision_rounding=rounding
            )
            > 0
        ):
            raise UserError(
                _(
                    "Only %(qty)s %(uom)s are available to produce in this work order. "
                    "The limit comes from the previous work order, the reserved "
                    "components or the quantity to produce.",
                    qty=self.available_production_qty,
                    uom=self.product_uom_id.name,
                )
            )
        for move in self._get_component_moves():
            consumed = float_round(
                qty * move.unit_factor, precision_rounding=move.product_uom.rounding
            )
            line = self.line_ids.filtered(lambda ln, move=move: ln.move_id == move)
            if line:
                line.qty_done += consumed
            else:
                self.env["mrp.workorder.line"].create(
                    {"workorder_id": self.id, "move_id": move.id, "qty_done": consumed}
                )
        self.qty_produced += qty

    def set_qty_produced(self, qty):
        """Lower the recorded quantity to ``qty``, giving back the consumption."""
        self.ensure_one()
        rounding = self.product_uom_id.rounding
        if self.state in ("done", "cancel"):
            raise UserError(
                _("A finished or cancelled work order cannot be corrected.")
            )
        if float_compare(qty, 0, precision_rounding=rounding) < 0:
            raise UserError(_("The quantity cannot be negative."))
        if float_compare(qty, self.qty_produced, precision_rounding=rounding) > 0:
            raise UserError(
                _(
                    "The correction can only lower the recorded quantity. "
                    "To record more, use Record production."
                )
            )
        previous = self._get_previous_workorders()
        if (
            previous
            and float_compare(
                qty, self.previous_wo_produced_qty, precision_rounding=rounding
            )
            > 0
        ):
            raise UserError(
                _(
                    "The quantity cannot exceed the one recorded by the previous work order."
                )
            )
        following = self.needed_by_workorder_ids.filtered(
            lambda wo: wo.state != "cancel"
        )
        if (
            following
            and float_compare(
                qty, max(following.mapped("qty_produced")), precision_rounding=rounding
            )
            < 0
        ):
            raise UserError(
                _(
                    "The next work order has already recorded more than this quantity. "
                    "Correct it first."
                )
            )
        if self.qty_produced:
            ratio = qty / self.qty_produced
            for line in self.line_ids:
                line.qty_done = float_round(
                    line.qty_done * ratio,
                    precision_rounding=line.product_uom_id.rounding,
                )
        self.qty_produced = qty

    def launch_production(self):
        """Post the recorded quantity to the manufacturing order.

        Only the last work order posts. A quantity lower than the planned one
        creates a backorder for the balance.
        """
        self.ensure_one()
        if not self.is_last_wo:
            raise UserError(
                _("Only the last work order can post to the manufacturing order.")
            )
        qty = self.qty_to_launch
        if float_compare(qty, 0, precision_rounding=self.product_uom_id.rounding) <= 0:
            raise UserError(_("There is no quantity to post."))
        production = self.production_id
        # components released after the recording (e.g. returned to stock) are
        # reserved again, so the lots to consume are proposed
        production.move_raw_ids.filtered(
            lambda m: m.state in ("confirmed", "partially_available")
        )._action_assign()
        production._check_tracked_components_have_lot()
        production.qty_producing = qty
        production._set_qty_producing(False)
        if production.product_tracking == "lot" and not production.lot_producing_id:
            # the lot the user did not choose on the order is proposed, as the
            # core does when the production is recorded in the work order
            production.action_generate_serial()
        self.qty_launched += qty
        partial = (
            float_compare(
                qty,
                production.product_qty,
                precision_rounding=production.product_uom_id.rounding,
            )
            < 0
        )
        return production.with_context(
            skip_backorder=True,
            skip_consumption=True,
            skip_immediate=True,
            mo_ids_to_backorder=production.ids if partial else False,
        ).button_mark_done()
