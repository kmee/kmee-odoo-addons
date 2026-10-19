# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class CommissionLineMixin(models.AbstractModel):
    _inherit = "commission.line.mixin"

    def _get_commission_amount(self, commission, subtotal, product, quantity):
        """Provisional amount for period commissions.

        The tier depends on everything sold in the settlement period, so until
        the settlement the first tier is used. The settlement recomputes it.
        """
        self.ensure_one()
        if commission and commission.commission_type == "period_section":
            base = commission._get_period_base_amount(subtotal, product, quantity)
            return base * commission.calculate_period_section() / 100.0
        return super()._get_commission_amount(commission, subtotal, product, quantity)
