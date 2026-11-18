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
            self._prepare_lines_to_sale_order_line(line, matched_line)
        return wizard.create_sale_order()

    def _prepare_lines_to_sale_order_line(self, line, matched_line):
        # Keep quantity selected in the quotation
        line.qty = matched_line.product_uom_qty
        # Propagate discount from the quotation line to wizard line (and then SO)
        if hasattr(line, "discount") and hasattr(matched_line, "discount"):
            line.discount = matched_line.discount

    def _prepare_common_blanket_order_fields(self, override_vals=None):
        self.ensure_one()
        blanket_order_fields = set(self.env["sale.blanket.order"].fields_get().keys())
        sale_order_fields = set(self.env["sale.order"].fields_get().keys())
        common_fields = blanket_order_fields.intersection(sale_order_fields)
        vals = {"blanket_order_id": self.id}
        skip_fields = self._get_skip_fields()
        for field in common_fields:
            if field not in skip_fields:
                value = getattr(self, field)
                vals[field] = value.id if hasattr(value, "id") else value
        if override_vals:
            vals.update(override_vals)
        return vals

    def action_create_increment_quotation(self):
        self.ensure_one()
        vals = self._prepare_common_blanket_order_fields(
            {
                "is_blanket_order_increment": True,
                "blanket_order_type": "amendment",
            }
        )
        sale_order = self.env["sale.order"].create(vals)
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
        vals = self._prepare_common_blanket_order_fields(
            {
                "blanket_order_type": "reference",
            }
        )
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
    def _get_skip_fields(cls):
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
