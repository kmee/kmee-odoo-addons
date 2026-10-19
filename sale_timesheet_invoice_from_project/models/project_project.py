# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class ProjectProject(models.Model):
    _inherit = "project.project"

    def action_create_invoice_from_projects(self):
        """Open the invoice wizard for the sales orders of the selected projects."""
        orders = (
            self.mapped("sale_order_id") | self.mapped("task_ids.sale_order_id")
        ).filtered(lambda so: so.invoice_status in ("to invoice", "no"))
        action = self.env["ir.actions.actions"]._for_xml_id(
            "sale.action_view_sale_advance_payment_inv"
        )
        action["context"] = {
            "active_model": "sale.order",
            "active_id": orders.id if len(orders) == 1 else False,
            "active_ids": orders.ids,
        }
        return action
