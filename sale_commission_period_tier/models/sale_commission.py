import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class SaleCommission(models.Model):
    _inherit = "sale.commission"

    commission_type = fields.Selection(
        selection_add=[("period_section", "Period sections")],
        ondelete={"period_section": "cascade"},
    )

    def calculate_period_section(self, total_amount=None):
        """Calculate commission percentage based on total amount for the period
        If total_amount is not provided, returns the first section percentage
        """
        self.ensure_one()

        if self.commission_type != "period_section":
            return 0.0

        sections = self.section_ids.sorted("amount_from")

        # If no total_amount provided, return first section
        if total_amount is None:
            return sections[:1].percent if sections else 0.0

        # Find applicable section
        for section in sections:
            if (
                section.amount_from
                <= total_amount
                <= (section.amount_to or float("inf"))
            ):
                return section.percent

        return 0.0
