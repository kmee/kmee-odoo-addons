# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError

MOVABLE_STATES = ["draft", "confirmed"]


class PurchaseRequisitionLine(models.Model):
    _name = "purchase.requisition.line"
    _inherit = ["purchase.requisition.line", "mail.thread"]

    product_qty = fields.Float(tracking=True)
    schedule_date = fields.Date(string="Scheduled Date")
    justificativa = fields.Text(string="Justification")
    has_justificativa = fields.Boolean(
        string="Has Justification",
        compute="_compute_has_justificativa",
        store=True,
    )
    has_quotation_line = fields.Boolean(
        compute="_compute_has_quotation_line",
        help="There are quantities of this product in quotations or orders.",
    )
    can_move = fields.Boolean(compute="_compute_can_move")

    @api.depends("justificativa")
    def _compute_has_justificativa(self):
        for line in self:
            line.has_justificativa = bool(line.justificativa)

    @api.depends(
        "product_id",
        "requisition_id.purchase_ids.state",
        "requisition_id.purchase_ids.order_line.product_id",
    )
    def _compute_has_quotation_line(self):
        for line in self:
            orders = line.requisition_id.purchase_ids.filtered(
                lambda o: o.state != "cancel"
            )
            line.has_quotation_line = bool(line.product_id) and (
                line.product_id in orders.order_line.product_id
            )

    @api.depends("requisition_id.state")
    def _compute_can_move(self):
        for line in self:
            line.can_move = line.requisition_id.state in MOVABLE_STATES

    def _check_can_move(self):
        self.ensure_one()
        if self.requisition_id.state not in MOVABLE_STATES:
            raise UserError(
                self.env._(
                    "The agreement is not in draft or confirmed state, "
                    "its lines cannot be moved."
                )
            )
        if self.qty_ordered:
            raise UserError(self.env._("This line already has ordered quantities."))

    def button_move_lines_to_different_requisition(self):
        self.ensure_one()
        self._check_can_move()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "purchase_requisition_line_delegate.purchase_requisition_delegate_act_window"
        )
        action["context"] = {
            "default_purchase_requisition_id": self.requisition_id.id,
            "default_purchase_requisition_line_id": self.id,
        }
        return action

    def action_show_justificativa(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": self.env._("Justification"),
                "message": self.justificativa or "",
                "type": "warning",
                "sticky": False,
            },
        }

    def action_view_quotations(self):
        self.ensure_one()
        orders = self.requisition_id.purchase_ids.filtered(
            lambda o: o.state != "cancel" and self.product_id in o.order_line.product_id
        )
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Quotations and Orders"),
            "res_model": "purchase.order",
            "view_mode": "list,form",
            "domain": [("id", "in", orders.ids)],
        }
