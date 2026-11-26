# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    explicit_bom_id = fields.Many2one(
        comodel_name="mrp.bom",
        string="Bill of Materials",
        domain="[('product_tmpl_id', '=', product_template_id)]",
        ondelete="restrict",
        help="Bill of materials used to manufacture this line, instead of the "
        "one Odoo would choose.",
    )
    production_notes = fields.Text(
        help="Instructions for the production, copied to the production request.",
    )
    created_after_sale_order_confirmed = fields.Boolean(
        help="The line was added after the sale order was confirmed.",
        copy=False,
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        orders = self.env["sale.order"].browse(
            [vals["order_id"] for vals in vals_list if vals.get("order_id")]
        )
        confirmed_ids = set(orders.filtered(lambda order: order.state == "sale").ids)
        for vals in vals_list:
            if vals.get("order_id") in confirmed_ids:
                vals["created_after_sale_order_confirmed"] = True
        return super().create(vals_list)

    @api.onchange("product_id")
    def _onchange_product_id_reset_explicit_bom(self):
        if (
            self.explicit_bom_id
            and self.explicit_bom_id.product_tmpl_id != self.product_id.product_tmpl_id
        ):
            self.explicit_bom_id = False

    def _prepare_procurement_values(self, group_id=False):
        values = super()._prepare_procurement_values(group_id)
        if self.explicit_bom_id:
            values["bom_id"] = self.explicit_bom_id
        if self.created_after_sale_order_confirmed:
            values["created_after_sale_order_confirmed"] = True
        return values
