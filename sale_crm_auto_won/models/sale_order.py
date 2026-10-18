# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrder(models.Model):

    _inherit = "sale.order"

    def action_confirm(self):
        for sale in self:
            if sale.opportunity_id:
                sale.opportunity_id.action_set_won_rainbowman()
        return super().action_confirm()
