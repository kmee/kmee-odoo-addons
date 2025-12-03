# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date
from inspect import signature

from dateutil.relativedelta import relativedelta

from odoo import models


class SaleCommissionMakeSettle(models.TransientModel):

    _inherit = "commission.make.settle"

    def _get_period_start(self, agent, date_to):
        if agent.settlement == "vinte_seis" and date_to:
            if date_to.day >= 26:
                return date(year=date_to.year, month=date_to.month, day=26)
            prev_month = date_to - relativedelta(months=1)
            return date(year=prev_month.year, month=prev_month.month, day=26)
        return self._call_super_get_period_start(agent, date_to)

    def _get_next_period_date(self, agent, current_date):
        if agent.settlement == "vinte_seis" and current_date:
            next_month = current_date + relativedelta(months=1)
            return date(year=next_month.year, month=next_month.month, day=26)
        return self._call_super_get_next_period_date(agent, current_date)

    def _call_super_get_period_start(self, agent, date_to):
        super_method = super()
        method = super_method._get_period_start
        params = signature(method).parameters
        if len(params) == 1:
            return method(agent)
        return method(agent, date_to)

    def _call_super_get_next_period_date(self, agent, current_date):
        super_method = super()
        method = super_method._get_next_period_date
        params = signature(method).parameters
        if len(params) == 1:
            return method(agent)
        return method(agent, current_date)
