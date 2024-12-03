# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrder(models.Model):

    _inherit = "sale.order"

    def action_pos_report(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/sale_order_pos_report_plain_text/{self.id}",
            "target": "new",
        }
