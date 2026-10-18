# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class ResPartner(models.Model):

    _inherit = "res.partner"

    def _get_name(self):
        name = super()._get_name()
        if self.ref:
            name = "[{}] {}".format(self.ref, name)
        return name
