from odoo import models

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _pc_extra_price_from_value_qty(self, config_line):
        """Soma price_extra proporcional a qty, se aplicável."""
        total = 0.0
        for value, qty in config_line.get_selected_values_with_qty():
            total += (value.price_extra or 0.0) * max(qty, 0.0)
        return total
