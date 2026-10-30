# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _zitron_report_buyer_contact(self):
        """Contact lines of the buyer (e-mail and phone) for the PDF header."""
        self.ensure_one()
        partner = self.user_id.partner_id
        if not partner:
            return []
        lines = []
        if partner.email:
            lines.append(partner.email)
        phone = partner.phone or partner.mobile
        if phone:
            lines.append(phone)
        return lines

    def _zitron_report_project_name(self):
        """Name of the project linked to the order, if any.

        ``project_id`` comes from ``project_purchase``, which is not a
        dependency of this module, so the field is looked up defensively.
        """
        self.ensure_one()
        if "project_id" not in self._fields or not self.project_id:
            return ""
        return self.project_id.display_name
