# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class SaleOrder(models.Model):

    _inherit = "sale.order"

    @api.depends("partner_id")
    def _compute_partner_invoice_id(self):
        super()._compute_partner_invoice_id()
        for order in self:
            if order.partner_invoice_id.company_type == "person":
                addr = order.partner_id.commercial_partner_id.address_get(
                    ["invoice"]
                )
                if addr.get("invoice"):
                    order.partner_invoice_id = addr["invoice"]

    @api.depends("partner_id")
    def _compute_partner_shipping_id(self):
        super()._compute_partner_shipping_id()
        for order in self:
            if order.partner_shipping_id.company_type == "person":
                addr = order.partner_id.commercial_partner_id.address_get(
                    ["delivery"]
                )
                if addr.get("delivery"):
                    order.partner_shipping_id = addr["delivery"]
