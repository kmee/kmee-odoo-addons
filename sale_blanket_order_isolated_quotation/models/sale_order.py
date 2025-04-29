# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import datetime

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    isolated_blanket_order_id = fields.Many2one(
        comodel_name="sale.blanket.order",
        inverse_name="isolated_quotation_id",
        readonly=True,
        ondelete="restrict",
        copy=False,
        string="Blanket Order",
    )

    def action_convert_to_blanket_order(self):
        self.ensure_one()
        sale_order_fields = self.env["sale.order"]._fields
        blanket_order_fields = self.env["sale.blanket.order"]._fields
        common_fields = set(sale_order_fields.keys()) & set(blanket_order_fields.keys())
        not_common_fields = set(sale_order_fields.keys()) - common_fields
        common_vals = {}
        skip_fields = [
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
        ]
        quotation_data_json = {
            name_field: value
            for name_field, value in self.read(not_common_fields)[0].items()
            if name_field not in skip_fields and value
        }
        for field in quotation_data_json:
            if isinstance(quotation_data_json[field], datetime.datetime):
                quotation_data_json[field] = quotation_data_json[field].isoformat()
        for field in common_fields:
            if field not in skip_fields:
                value = getattr(self, field)
                common_vals[field] = value.id if hasattr(value, "id") else value

        blanket_order_line_fields = self.env["sale.blanket.order.line"]._fields
        sale_order_line_fields = self.env["sale.order.line"]._fields
        line_common_fields = set(blanket_order_line_fields.keys()) & set(
            sale_order_line_fields.keys()
        )
        map_values = {}
        map_values["original_uom_qty"] = "product_uom_qty"
        line_vals = []
        for line in self.order_line:
            vals = {"order_id": False}  # será associado automaticamente
            for field in line_common_fields:
                value = getattr(line, field)
                vals[field] = value.id if hasattr(value, "id") else value
            for field in map_values:
                value = getattr(line, map_values[field])
                vals[field] = value.id if hasattr(value, "id") else value
            line_vals.append((0, 0, vals))

        blanket_order_vals = {}
        blanket_order_vals.update(common_vals)
        blanket_order_vals["isolated_quotation_id"] = self.id
        blanket_order_vals["line_ids"] = line_vals
        blanket_order_vals["quotation_data_json"] = quotation_data_json
        bo = self.env["sale.blanket.order"].create(blanket_order_vals)
        bo.action_confirm()
        self.isolated_blanket_order_id = bo.id
        return {
            "type": "ir.actions.act_window",
            "name": "Blanket Order",
            "res_model": "sale.blanket.order",
            "view_mode": "form",
            "res_id": bo.id,
            "target": "current",
        }


# order_id = fields.Many2one(
#         comodel_name="sale.order",
#         string="Order",
#         readonly=True,
#         ondelete="restrict",
#         copy=False,
#         help="For Quotation, this field references to its Sales Order",
#     )
