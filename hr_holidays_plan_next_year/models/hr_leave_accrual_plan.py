# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from dateutil.relativedelta import relativedelta

from odoo import fields, models


class HrLeaveAllocation(models.Model):

    _inherit = "hr.leave.allocation"

    def _end_of_year_accrual(self):
        today = fields.Date.today()
        first_day_this_year = today + relativedelta(month=1, day=1)
        for allocation in self:
            current_level = allocation._get_current_accrual_plan_level_id(
                first_day_this_year
            )[0]
            if current_level and current_level.frequency == "next_year":
                continue
            else:
                super(HrLeaveAllocation, allocation)._end_of_year_accrual()


class HrLeaveAccrualPlan(models.Model):

    _inherit = "hr.leave.accrual.level"

    frequency = fields.Selection(
        selection_add=[("next_year", "Next Year")],
        ondelete={"next_year": "set default"},
    )

    def _get_next_date(self, last_call):
        """
        Returns the next date with the given last call
        """
        result = super()._get_next_date(last_call)

        if self.frequency == "next_year":
            date = last_call
            if last_call < date:
                result = date
            else:
                result = last_call + relativedelta(years=1)
        return result

    def _get_previous_date(self, last_call):
        """
        Returns the date a potential previous call would have been at
        For example if you have a monthly level giving 16/02 would return 01/02
        Contrary to `_get_next_date` this function will return the 01/02 if that date is given
        """
        result = super()._get_previous_date(last_call)

        if self.frequency == "next_year":
            year_date = last_call
            if last_call >= year_date:
                result = year_date
            else:
                result = last_call + relativedelta(years=-2)

        return result

    _sql_constraints = [
        (
            "check_dates",
            "CHECK(1=1)",
            """The employee, department, company,
            or employee category of this request is missing.
             Please make sure that your user login is linked to an employee.""",
        ),
    ]
