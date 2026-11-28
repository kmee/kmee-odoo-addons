# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class MrpProductionRequestCreateMo(models.TransientModel):
    _inherit = "mrp.production.request.create.mo"

    def _prepare_manufacturing_order(self):
        vals = super()._prepare_manufacturing_order()
        sale_line = self.mrp_production_request_id.sale_line_id
        if sale_line:
            vals["sale_line_id"] = sale_line.id
        return vals
