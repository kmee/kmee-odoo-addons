# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = "res.config.settings"

    logo_order_so_pos_report = fields.Binary(
        string="Company Logo",
        related="company_id.logo_order_so_pos_report",
        readonly=False,
    )
