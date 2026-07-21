# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class CommissionCron(models.TransientModel):
    _name = "commission.cron"
    _description = "Commission Cron Helper"

    @api.model
    def cron_generate_next_month_commissions(self):
        """Create the standard settlement wizard for next month and run it."""
        next_month_date = fields.Date.context_today(self) + relativedelta(months=1)

        settle_wizard_model = self.env["commission.make.settle"].sudo()

        wizard = settle_wizard_model.create(
            {
                "date_to": next_month_date,
            }
        )

        wizard.action_settle()
