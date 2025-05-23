# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleBlanketOrder(models.Model):

    _inherit = "sale.blanket.order"

    quotation_data_json = fields.Json()

    isolated_quotation_id = fields.Many2one(
        comodel_name="sale.order",
        readonly=True,
        copy=False,
        string="Quotation",
    )

    def _compute_state(self):
        today = fields.Date.today()
        for order in self:
            if order.validity_date and order.validity_date <= today:
                order.state = "expired"
            else:
                order.state = "open"

    def create_sale_order_from_wizard(self, sale_order_lines):
        wizard = (
            self.env["sale.blanket.order.wizard"]
            .with_context(active_ids=self.line_ids.ids, active_id=self.id)
            .create({})
        )
        for line in wizard.line_ids:
            matched_line = sale_order_lines.filtered(
                lambda sale_line: sale_line.blanket_order_line_id
                == line.blanket_line_id
            )
            line.qty = matched_line.product_uom_qty
        return wizard.create_sale_order()

    def action_create_increment_quotation(self):
        """Create a new quotation for incrementing the blanket order."""
        self.ensure_one()

        # Create sale order with lines from blanket order
        vals = {
            "partner_id": self.partner_id.id,
            "is_blanket_order_increment": True,
            "blanket_order_id": self.id,
            "blanket_order_type": "amendment",  # Forçar tipo amendment
        }

        sale_order = self.env["sale.order"].create(vals)

        # Create sale order lines
        for line in self.line_ids:
            vals = sale_order._prepare_blanket_order_line_values(line)
            vals["order_id"] = sale_order.id
            self.env["sale.order.line"].create(vals)

        return {
            "type": "ir.actions.act_window",
            "name": "Increment Quotation",
            "res_model": "sale.order",
            "view_mode": "form",
            "res_id": sale_order.id,
            "target": "current",
        }
