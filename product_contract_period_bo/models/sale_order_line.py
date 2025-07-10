# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrderLine(models.Model):

    _inherit = "sale.order.line"

    use_period_quantity = fields.Boolean(
        related="product_id.uom_id.use_period_quantity"
    )

    product_uom_qty = fields.Float(
        string="Quantity",
        digits="Product Unit of Measure",
        default=1.0,
        store=True,
        readonly=False,
        required=True,
    )

    def _prepare_sale_order_line_values(self):
        res = super()._prepare_sale_order_line_values()
        fields_map = {
            "period_qty": self.period_qty,
            "period_count": self.period_count,
            "date_start": self.date_start,
            "date_end": self.date_end,
        }
        res.update(fields_map)
        return res

    @api.onchange("period_qty", "period_count", "price_unit", "discount")
    def _onchange_period(self):
        for record in self:
            if record.use_period_quantity:
                record.product_uom_qty = record.period_qty * record.period_count
                record.date_end = record._get_date_end()

    def write(self, vals):
        for record in self:
            use_period = vals.get("use_period_quantity", record.use_period_quantity)
            if use_period:
                period_qty = vals.get("period_qty", record.period_qty)
                period_count = vals.get("period_count", record.period_count)
                vals["product_uom_qty"] = period_qty * period_count
        return super(SaleOrderLine, self.with_context(check_qty_unprotect=vals)).write(
            vals
        )

    def _get_protected_fields(self):
        fields = super()._get_protected_fields()
        ctx = self.env.context.get("check_qty_unprotect")
        if (
            ctx
            and all(k in ctx for k in ("product_uom_qty", "original_bo_qty"))
            and ctx["original_bo_qty"] == 0
        ):
            fields = [
                f for f in fields if f not in ["product_uom_qty", "original_bo_qty"]
            ]
        return fields
