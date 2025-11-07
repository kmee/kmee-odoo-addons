# Copyright (C) 2025-Today - KMEE (<http://www.kmee.com.br>).
# @author Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    is_intercompany_partner = fields.Boolean(
        compute="_compute_is_intercompany_partner",
        readonly=False,
        store=True,
    )
    partner_pricelist_id = fields.Many2one(
        compute="_compute_is_intercompany_partner",
        comodel_name="product.pricelist",
        string="Interco Pricelist",
        readonly=True,
        states={"draft": [("readonly", False)]},
        store=True,
    )
    partner_company_id = fields.Many2one(
        compute="_compute_is_intercompany_partner",
        comodel_name="res.company",
        string="Partner Company",
        readonly=True,
        states={"draft": [("readonly", False)]},
        store=True,
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

    def button_approve(self, force=False):
        for order in self:
            if order.currency_id != order.partner_pricelist_id.currency_id:
                raise ValidationError(
                    _(
                        "You cannot create SO from PO because sale price list currency "
                        "is different than purchase price list currency.\n"
                        "Please fix it manually before approving the PO.\n\n"
                    )
                )
        return super().button_approve(force=force)

    def inter_company_create_sale_order(self, company):
        """
        Temporarilly force currency_id in sale order to match partner property pricelist
        currency.

        Store the original currency and restore it after calling super.
        """

        original_currencies = {}
        for rec in self:
            original_currencies[rec.id] = rec.currency_id
            rec.currency_id = rec.partner_id.property_product_pricelist.currency_id

        res = super().inter_company_create_sale_order(company)

        for rec in self:
            rec.currency_id = original_currencies[rec.id]

        return res
