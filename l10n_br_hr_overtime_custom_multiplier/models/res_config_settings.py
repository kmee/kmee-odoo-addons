# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = "res.config.settings"

    saturday_overtime_multiplier = fields.Char(
        config_parameter="saturday_overtime_multiplier",
    )
    sunday_holidays_overtime_multiplier = fields.Char(
        config_parameter="sunday_holidays_overtime_multiplier",
    )
    business_days_over_2_hours_overtime_multiplier = fields.Char(
        config_parameter="business_days_over_2_hours_overtime_multiplier",
    )
    business_days_under_2_hours_overtime_multiplier = fields.Char(
        config_parameter="business_days_under_2_hours_overtime_multiplier",
    )
