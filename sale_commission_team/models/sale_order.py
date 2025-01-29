# Copyright 2021 KMEE - Luis Felipe Mileo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrdeLine(models.Model):
    _inherit = "sale.order.line"

    def _prepare_agents_vals_partner(self, partner_id):
        """Add salesman agent if configured so and no other commission
        already populated.
        """
        res = super()._prepare_agents_vals_partner(partner_id)
        if not res:
            if partner_id and self.team_id:
                return self._prepare_agents_team_vals_partner(partner_id, self.team_id)
        return res
