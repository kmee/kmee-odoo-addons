# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    ordering_date = fields.Date(string="Scheduled Order Date")

    def button_display_total_qties(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "purchase_requisition_line_delegate.action_display_total_qties"
        )
        action["context"] = {"default_requisition_id": self.id}
        return action
