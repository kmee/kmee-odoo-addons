# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.exceptions import ValidationError

from ..models.purchase_requisition_line import MOVABLE_STATES


class PurchaseRequisitionDelegate(models.TransientModel):
    _name = "purchase.requisition.delegate"
    _description = "Delegate Purchase Agreement Line"

    purchase_requisition_id = fields.Many2one(
        "purchase.requisition", string="Purchase Agreement", required=True
    )
    purchase_requisition_line_id = fields.Many2one(
        "purchase.requisition.line", string="Line", required=True
    )
    to_purchase_requisition_id = fields.Many2one(
        "purchase.requisition", string="Move to", required=True
    )

    def doit(self):
        self.ensure_one()
        target = self.to_purchase_requisition_id
        if target.state not in MOVABLE_STATES:
            raise ValidationError(
                self.env._("The target agreement must be in draft or confirmed state.")
            )
        line = self.purchase_requisition_line_id
        line._check_can_move()
        line.requisition_id = target
        return {"type": "ir.actions.act_window_close"}
