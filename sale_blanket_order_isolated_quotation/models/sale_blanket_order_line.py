# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo import api, fields, models


class BlanketOrderLine(models.Model):
    _inherit = "sale.blanket.order.line"

    # Align with sale.order.line API
    discount = fields.Float(string="Discount (%)", default=0.0)

    price_subtotal = fields.Monetary(
        string="Subtotal",
        compute="_compute_amount",
        currency_field="currency_id",
        store=True,
    )

    @api.depends(
        "original_uom_qty",
        "price_unit",
        "taxes_id",
        "order_id.partner_id",
        "product_id",
        "currency_id",
        "discount",
    )
    def _compute_amount(self):
        for line in self:
            # Compute on discounted unit price and the line quantity
            effective_price = (line.price_unit or 0.0) * (
                1.0 - (line.discount or 0.0) / 100.0
            )
            taxes = line.taxes_id.compute_all(
                effective_price,
                line.currency_id,
                line.original_uom_qty or 0.0,
                product=line.product_id,
                partner=line.order_id.partner_id,
            )
            line.update(
                {
                    "price_tax": sum(
                        t.get("amount", 0.0) for t in taxes.get("taxes", [])
                    ),
                    "price_total": taxes.get("total_included", 0.0),
                    "price_subtotal": taxes.get("total_excluded", 0.0),
                }
            )
