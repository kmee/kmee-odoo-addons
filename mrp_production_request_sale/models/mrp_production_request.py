# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MrpProductionRequest(models.Model):
    _inherit = "mrp.production.request"

    sale_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Sale Order Line",
        copy=False,
        index=True,
    )
    origin_sale_id = fields.Many2one(
        comodel_name="sale.order",
        string="Sale Order",
        compute="_compute_origin_sale_id",
        store=True,
        index=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        related="origin_sale_id.partner_id",
    )
    sale_person_id = fields.Many2one(
        comodel_name="res.users",
        string="Salesperson",
        related="origin_sale_id.user_id",
    )
    notes_from_so = fields.Text(string="Sale Order Notes")

    @api.depends("sale_line_id", "origin")
    def _compute_origin_sale_id(self):
        for request in self:
            sale = request.sale_line_id.order_id
            if not sale and request.origin:
                sale = self.env["sale.order"].search(
                    [("name", "=", request.origin)], limit=1
                )
            request.origin_sale_id = sale

    @api.model_create_multi
    def create(self, vals_list):
        requests = super().create(vals_list)
        for request in requests:
            request._set_sale_line_data()
        return requests

    def _set_sale_line_data(self):
        """Take the bill of materials and the production notes from the sale
        line when the request was created by hand with the sale order as origin."""
        self.ensure_one()
        line = self.sale_line_id
        if not line and self.origin_sale_id:
            line = fields.first(
                self.origin_sale_id.order_line.filtered(
                    lambda sale_line: sale_line.product_id == self.product_id
                )
            )
            self.sale_line_id = line
        if not line:
            return
        if line.explicit_bom_id:
            self.bom_id = line.explicit_bom_id
        if line.production_notes and not self.notes_from_so:
            self.notes_from_so = line.production_notes
