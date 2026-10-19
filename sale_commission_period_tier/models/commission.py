# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class Commission(models.Model):
    _inherit = "commission"

    commission_type = fields.Selection(
        selection_add=[("period_section", "Period sections")],
        ondelete={"period_section": "cascade"},
    )

    def calculate_period_section(self, total_amount=None):
        """Return the commission percentage for the total sold in the period.

        The first section that contains the total (both limits included) wins.
        Without a total, the percentage of the first section is returned: it is the rate
        shown on the invoice lines until the commissions are settled.
        """
        self.ensure_one()
        if self.commission_type != "period_section" or not self.section_ids:
            return 0.0
        if total_amount is None:
            return self.section_ids[0].percent
        for section in self.section_ids:
            if section.amount_from <= total_amount <= section.amount_to:
                return section.percent
        return 0.0

    def _get_period_base_amount(self, subtotal, product, quantity):
        """Amount of a line that enters the period total and the commission."""
        self.ensure_one()
        if product.commission_free:
            return 0.0
        if self.amount_base_type == "net_amount":
            return max(0.0, subtotal - product.standard_price * quantity)
        return subtotal
