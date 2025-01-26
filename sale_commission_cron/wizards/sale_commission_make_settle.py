# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class SaleCommissionMakeSettle(models.TransientModel):
    _inherit = "sale.commission.make.settle"

    @api.model
    def cron_generate_next_month_commissions(self):
        # Calculate the date for next month
        next_month_date = fields.Date.today() + relativedelta(months=1)

        # Create the wizard record
        wizard = self.create(
            {
                "date_to": next_month_date,
                "date_payment_to": next_month_date,
            }
        )

        # Process the commissions
        wizard.action_settle()
