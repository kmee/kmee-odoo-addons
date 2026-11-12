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

    def _zitron_delivery_informed(self):
        """Whether the user set a delivery date on the line, for the PDF.

        Odoo never leaves ``date_planned`` empty: when nobody sets it, it is
        computed as the order date (``date_order``) plus the vendor lead time.
        The default is therefore exactly ``date_order`` (second precision)
        when there is no vendor delay, so a line whose ``date_planned`` is
        identical to the order's ``date_order`` is treated as "not informed".
        The comparison is on the full datetime (a UTC instant, so independent
        of the user timezone). A date typed by the user on the same day gets a
        different time of day, so it is not mistaken for the default.
        """
        self.ensure_one()
        date_planned = self.date_planned
        date_order = self.order_id.date_order
        if not date_planned:
            return False
        if not date_order:
            return True
        return date_planned.replace(microsecond=0) != date_order.replace(microsecond=0)
