# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class ResPartner(models.Model):

    _inherit = "res.partner"

    @api.depends("ref")
    def _compute_display_name(self):
        return super()._compute_display_name()

    def _get_name(self):
        name = super()._get_name()
        if self.ref:
            name = "[{}] {}".format(self.ref, name)
        return name
