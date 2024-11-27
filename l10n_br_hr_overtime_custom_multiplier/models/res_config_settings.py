# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = "res.config.settings"

    saturday_overtime_multiplier = fields.Char(string='Saturday Overtime Multiplier', config_parameter='saturday_overtime_multiplier')
    sunday_holidays_overtime_multiplier = fields.Char(string='Sunday and Holidays Overtime Multiplier', config_parameter='sunday_holidays_overtime_multiplier')
    business_days_over_2_hours_overtime_multiplier = fields.Char(string='Business Days Over 2 Hours Overtime Multiplier', config_parameter='business_days_over_2_hours_overtime_multiplier')
    business_days_under_2_hours_overtime_multiplier = fields.Char(string='Business Days Under 2 Hours Overtime Multiplier', config_parameter='business_days_under_2_hours_overtime_multiplier')
