# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.depends("ref")
    def _compute_display_name(self):
        super()._compute_display_name()
        for partner in self.filtered("ref"):
            partner.display_name = f"[{partner.ref}] {partner.display_name}"
