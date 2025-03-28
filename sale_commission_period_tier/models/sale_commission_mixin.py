from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import models


class SaleCommissionLineMixin(models.AbstractModel):
    _inherit = "sale.commission.line.mixin"

    def _get_commission_amount(
        self, commission, subtotal, product, quantity, order_line=False
    ):
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

            if hasattr(self, "move_id"):
                # Invoice line
                date = self.move_id.invoice_date
            elif order_line and hasattr(order_line, "order_id"):
                # Sale order line
                date = order_line.order_id.date_order.date()
            else:
                date = datetime.now().date()

            # Calculate commission based on period total
            percentage = commission.calculate_period_section(
                self.agent_id,
                date.replace(day=1),  # First day of the month
                date.replace(day=1)
                + relativedelta(months=1, days=-1),  # Last day of the month
            )
            return subtotal * percentage / 100

        return super()._get_commission_amount(
            commission, subtotal, product, quantity, order_line
        )
