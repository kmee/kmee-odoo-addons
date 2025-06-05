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

    def action_create_reference_quotation(self):
        self.ensure_one()

        blanket_order_fields = set(self.env["sale.blanket.order"].fields_get().keys())
        sale_order_fields = set(self.env["sale.order"].fields_get().keys())
        common_fields = blanket_order_fields.intersection(sale_order_fields)
        vals = {
            "blanket_order_id": self.id,
            "blanket_order_type": "reference",
        }
        skip_fields = self._get_skip_fields()
        for field in common_fields:
            if field not in skip_fields:
                value = getattr(self, field)
                vals[field] = value.id if hasattr(value, "id") else value
        sale_order = self.env["sale.order"].create(vals)

        for line in self.line_ids:
            line_vals = sale_order._prepare_blanket_order_line_values(line)
            line_vals["order_id"] = sale_order.id
            self.env["sale.order.line"].create(line_vals)

        return {
            "type": "ir.actions.act_window",
            "name": "Reference Quotation",
            "res_model": "sale.order",
            "view_mode": "form",
            "res_id": sale_order.id,
            "target": "current",
        }

    @classmethod
    def _get_skip_fields(self):
        return [
            "message_follower_ids",
            "message_ids",
            "__last_update",
            "message_partner_ids",
            "date_order",
            "expected_date",
            "name",
            "state",
            "display_type",
            "display_name",
            "access_url",
            "id",
        ]
