# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HrLeave(models.Model):

    _inherit = "hr.leave"

    @api.model
    def _generate_hour_selection(self):
        selection = []
        for h in range(0, 24):
            for m in range(0, 60, 5):
                float_minute = m / 60
                float_hour = h + float_minute
                suffix = "AM" if h < 12 else "PM"
                display_hour = (
                    h if 1 <= h <= 12 else (12 if h == 0 or h == 12 else h - 12)
                )
                display = f"{display_hour}:{m:02d} {suffix}"
                selection.append((str(float_hour), display))
        return selection

    request_hour_from = fields.Selection(
        selection=_generate_hour_selection, string="Hour from"
    )
    request_hour_to = fields.Selection(
        selection=_generate_hour_selection, string="Hour to"
    )
