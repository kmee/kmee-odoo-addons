# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class SaleCommissionCron(models.TransientModel):
    _name = "sale.commission.cron"
    _description = "Sale Commission Cron Helper"

    @api.model
    def cron_generate_next_month_commissions(self):
        """Create the standard settlement wizard for next month and run it."""
        # Calculate the date for next month
        next_month_date = fields.Date.context_today(self) + relativedelta(months=1)

        # Use the original settlement wizard model
        settle_wizard_model = self.env["sale.commission.make.settle"].sudo()

        # Create the wizard record
        wizard = settle_wizard_model.create(
            {
                "date_to": next_month_date,
                "date_payment_to": next_month_date,
            }
        )

        # Process the commissions
        wizard.action_settle()
