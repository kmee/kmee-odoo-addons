# Copyright (C) 2025-Today - KMEE (<http://www.kmee.com.br>).
# Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _action_confirm(self):
        res = super()._action_confirm()
        for order in self:
            po_ids = order._get_purchase_orders()
            for po in po_ids:
                if order.currency_id != po.currency_id:
                    po.currency_id = order.currency_id
                    # Recompute prices on PO lines
                    for line in po.order_line:
                        line._onchange_quantity()
        return res
