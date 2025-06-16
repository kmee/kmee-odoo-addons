# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleBlanketOrderWizard(models.TransientModel):

    _inherit = "sale.blanket.order.wizard"

    def _prepare_so_line_vals(self, line):
        res = super()._prepare_so_line_vals(line)
        so_reference_id = self.env.context.get("so_reference_id")
        if so_reference_id:
            so = self.env["sale.order"].browse(so_reference_id)
            matching_line = so.order_line.filtered(
                lambda line_obj: line_obj.blanket_order_line_id.id
                == line.blanket_line_id.id
            )
            if matching_line:
                fields_map = {
                    "period_qty": matching_line.period_qty,
                    "period_count": matching_line.period_count,
                    "date_start": matching_line.date_start,
                    "date_end": matching_line.date_end,
                }
                res.update(fields_map)
        return res

    @api.model
    def _default_lines_custom(self, lines):
        for line in lines:
            line_data = line[2]
            blanket_line = self.env["sale.blanket.order.line"].browse(
                line_data["blanket_line_id"]
            )

            line_data.update(
                {
                    "period_qty": blanket_line.period_qty,
                    "period_count": blanket_line.period_count,
                    "date_start": blanket_line.date_start,
                    "date_end": blanket_line.date_end,
                }
            )

        return lines

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if "order_line" in fields_list:
            base_lines = self._default_lines()
            defaults["order_line"] = self._default_lines_custom(base_lines)
        return defaults


class BlanketOrderWizardLine(models.TransientModel):
    _inherit = "sale.blanket.order.wizard.line"

    period_qty = fields.Float()
    period_count = fields.Float()
    date_start = fields.Date()
    date_end = fields.Date()
