# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import models


class SaleCommissionMakeSettle(models.TransientModel):

    _inherit = "sale.commission.make.settle"

    def _get_period_start(self, agent, date_to):
        if agent.settlement == "vinte_seis":
            if date_to.day >= 26:
                return date(month=date_to.month, year=date_to.year, day=26)
            else:
                prev_month = date_to - relativedelta(months=1)
                return date(month=prev_month.month, year=prev_month.year, day=26)
        return super()._get_period_start(agent, date_to)

    def _get_next_period_date(self, agent, current_date):
        if agent.settlement == "vinte_seis":
            next_month = current_date + relativedelta(months=1)
            return date(month=next_month.month, year=next_month.year, day=26)
        return super()._get_next_period_date(agent, current_date)
