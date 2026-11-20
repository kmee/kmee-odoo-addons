# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _prepare_purchase_request_line(self, request_id, procurement):
        vals = super()._prepare_purchase_request_line(request_id, procurement)
        buffer = procurement.values.get("buffer_id")
        if buffer:
            vals["buffer_id"] = buffer.id
        return vals
