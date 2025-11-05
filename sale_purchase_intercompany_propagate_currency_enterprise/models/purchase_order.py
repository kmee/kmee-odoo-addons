# Copyright (C) 2025-Today - KMEE (<http://www.kmee.com.br>).
# @author Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    is_intercompany_partner = fields.Boolean(
        compute="_compute_is_intercompany_partner",
        store=True,
    )
    partner_pricelist_id = fields.Many2one(
        comodel_name="product.pricelist",
        string="Pricelist",
        readonly=False,
    )
    partner_company_id = fields.Many2one(
        comodel_name="res.company",
        string="Partner Company",
    )

    @api.depends("partner_id")
    def _compute_is_intercompany_partner(self):
        company_ids = self.env["res.company"].sudo().search([])
        for po in self:
            if po.partner_id.is_company and po.partner_id in company_ids.mapped(
                "partner_id"
            ):
                po.is_intercompany_partner = True
                po.partner_pricelist_id = po.partner_id.property_product_pricelist
                po.partner_company_id = company_ids.filtered(
                    lambda c: c.partner_id == po.partner_id
                )
            else:
                po.is_intercompany_partner = False
                po.partner_pricelist_id = False
                po.partner_company_id = False

    def _prepare_sale_order_data(self, name, partner, company, direct_delivery_address):
        res = super()._prepare_sale_order_data(
            name, partner, company, direct_delivery_address
        )
        if self.partner_pricelist_id:
            res["pricelist_id"] = self.partner_pricelist_id.id
            # res["currency_id"] = self.currency_id.id
        return res
