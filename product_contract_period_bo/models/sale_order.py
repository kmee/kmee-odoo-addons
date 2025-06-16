# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrder(models.Model):

    _inherit = "sale.order"

    def _prepare_blanket_order_line_values(self, bo_line):
        res = super()._prepare_blanket_order_line_values(bo_line)
        fields_map = {
            "period_qty": bo_line.period_qty,
            "period_count": bo_line.period_count,
            "date_start": bo_line.date_start,
            "date_end": bo_line.date_end,
        }
        res.update(fields_map)
        return res
