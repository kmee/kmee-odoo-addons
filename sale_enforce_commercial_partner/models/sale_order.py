# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class SaleOrder(models.Model):

    _inherit = "sale.order"

    @api.onchange("partner_id")
    def onchange_partner_id(self):
        res = super(SaleOrder, self).onchange_partner_id()
        add_list = []
        if self.partner_invoice_id.company_type == "person":
            add_list.append("invoice")
        if self.partner_shipping_id.company_type == "person":
            add_list.append("delivery")

        if add_list:
            addr = self.partner_id.commercial_partner_id.address_get(
                ["delivery", "invoice"]
            )
            values = {}
            if addr.get("invoice"):
                values["partner_invoice_id"] = addr["invoice"]
            if addr.get("delivery"):
                values["partner_shipping_id"] = addr["delivery"]
            self.update(values)
        return res
