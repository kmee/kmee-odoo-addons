# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _zitron_report_uom_label(self):
        """Abbreviated unit of measure for the PDF ("kg", "m", "pç", "un").

        Uses the fiscal (SPED) code of the unit when it is short enough to be
        an abbreviation, otherwise the unit name.
        """
        self.ensure_one()
        uom = self.product_uom
        code = uom.code or ""
        if code and len(code) <= 5:
            return code.lower()
        return uom.name or ""
