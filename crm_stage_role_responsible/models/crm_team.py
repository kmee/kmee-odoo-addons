# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CrmTeam(models.Model):

    _inherit = "crm.team"

    hide_bdr = fields.Boolean(string="Hide BDR", default=False)
    hide_sdr = fields.Boolean(string="Hide SDR", default=False)
    hide_hunter = fields.Boolean(default=False)
    hide_closer = fields.Boolean(default=False)
    hide_farmer = fields.Boolean(default=False)
