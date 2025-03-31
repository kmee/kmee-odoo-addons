from odoo import models


class SaleCommissionLineMixin(models.AbstractModel):
    _inherit = "sale.commission.line.mixin"

    def _get_commission_amount(self, commission, subtotal, product, quantity):
        """Calculate commission amount based on the commission type"""
        self.ensure_one()

        if commission.commission_type == "period_section":
            # For period-based commission, get the date from the invoice or order
            if self.env.context.get("period_commission_recalculation"):
                return (
                    self.env.context.get("period_commission_recalculation")
                    * subtotal
                    / 100
                )
            # Calculate commission based on period total
            percentage = commission.calculate_period_section()
            return subtotal * percentage / 100

        return super()._get_commission_amount(commission, subtotal, product, quantity)
