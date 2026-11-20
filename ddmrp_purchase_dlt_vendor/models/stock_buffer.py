# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class StockBuffer(models.Model):
    _inherit = "stock.buffer"

    @api.depends(
        "buffer_profile_id.dlt_vendor_policy",
        "product_id.seller_ids.rfq_approved",
    )
    def _compute_dlt(self):
        res = super()._compute_dlt()
        for rec in self:
            policy = rec.buffer_profile_id.dlt_vendor_policy
            if rec.buffer_profile_id.item_type != "purchased" or policy in (
                False,
                "first",
            ):
                continue
            sellers = rec._get_product_sellers()
            if policy == "worst_approved":
                sellers = sellers.filtered("rfq_approved") or sellers
            delays = [s.delay for s in sellers if s.delay]
            if delays:
                rec.dlt = max(delays)
        return res
