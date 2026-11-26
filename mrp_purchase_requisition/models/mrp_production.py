# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    requisition_line_ids = fields.Many2many(
        comodel_name="purchase.requisition.line",
        compute="_compute_purchase_requisition",
    )
    requisition_ids = fields.Many2many(
        comodel_name="purchase.requisition",
        compute="_compute_purchase_requisition",
    )
    purchase_ids = fields.Many2many(
        comodel_name="purchase.order",
        compute="_compute_purchase_requisition",
    )
    purchase_move_ids = fields.Many2many(
        comodel_name="stock.move",
        compute="_compute_purchase_requisition",
    )
    requisition_line_count = fields.Integer(compute="_compute_purchase_requisition")
    requisition_count = fields.Integer(compute="_compute_purchase_requisition")
    purchase_count = fields.Integer(compute="_compute_purchase_requisition")
    purchase_move_count = fields.Integer(compute="_compute_purchase_requisition")

    @api.depends("move_raw_ids.product_id")
    def _compute_purchase_requisition(self):
        line_model = self.env["purchase.requisition.line"].sudo()
        for production in self:
            lines = line_model.search([("production_id", "=", production.id)])
            requisitions = lines.requisition_id
            orders = requisitions.purchase_ids.filtered(
                lambda order: order.state in ("purchase", "done")
            )
            components = production.move_raw_ids.product_id
            moves = orders.picking_ids.move_ids.filtered(
                lambda move, components=components: move.product_id in components
            )
            production.requisition_line_ids = lines
            production.requisition_ids = requisitions
            production.purchase_ids = orders
            production.purchase_move_ids = moves
            production.requisition_line_count = len(lines)
            production.requisition_count = len(requisitions)
            production.purchase_count = len(orders)
            production.purchase_move_count = len(moves)

    def button_create_purchase_requisition(self):
        self.ensure_one()
        return self.env["ir.actions.actions"]._for_xml_id(
            "mrp_purchase_requisition." "mrp_production_purchase_requisition_act_window"
        ) | {"context": {"default_production_id": self.id}}

    def _action_view_records(self, xmlid, records):
        action = self.env["ir.actions.actions"]._for_xml_id(xmlid)
        action["domain"] = [("id", "in", records.ids)]
        action["context"] = {}
        return action

    def action_view_requisition_lines(self):
        return self._action_view_records(
            "mrp_purchase_requisition.action_requisition_lines",
            self.requisition_line_ids,
        )

    def action_view_requisitions(self):
        return self._action_view_records(
            "purchase_requisition.action_purchase_requisition", self.requisition_ids
        )

    def action_view_purchase_orders(self):
        return self._action_view_records(
            "purchase.purchase_form_action", self.purchase_ids
        )

    def action_view_purchase_moves(self):
        return self._action_view_records(
            "stock.stock_move_action", self.purchase_move_ids
        )
