# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase


class TestHrEmployeeVacationLog(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({"name": "Funcionário"})
        cls.period = cls.env["hr.employee.vacation.period"].create(
            {"employee_id": cls.employee.id, "date_from": date(2025, 3, 10)}
        )

    def _create_vacation(self, date_from, date_to, **values):
        return self.env["hr.employee.vacation"].create(
            {
                "employee_id": self.employee.id,
                "period_id": self.period.id,
                "date_from": date_from,
                "date_to": date_to,
                **values,
            }
        )

    def test_period_dates_and_balance(self):
        self.assertEqual(self.period.date_to, date(2026, 3, 9))
        self.assertEqual(self.period.deadline, date(2027, 2, 9))
        self.assertEqual(self.period.remaining_days, 30)
        self._create_vacation(date(2026, 4, 1), date(2026, 4, 20))
        self._create_vacation(date(2026, 8, 3), date(2026, 8, 7), cash_bonus=True)
        self.assertEqual(self.period.taken_days, 25)
        self.assertEqual(self.period.remaining_days, 5)

    def test_vacation_days_and_dates_check(self):
        vacation = self._create_vacation(date(2026, 4, 1), date(2026, 4, 20))
        self.assertEqual(vacation.days, 20)
        with self.assertRaises(ValidationError):
            self._create_vacation(date(2026, 4, 20), date(2026, 4, 1))

    def test_period_must_belong_to_the_employee(self):
        other = self.env["hr.employee"].create({"name": "Outro Funcionário"})
        with self.assertRaises(ValidationError):
            self.env["hr.employee.vacation"].create(
                {
                    "employee_id": other.id,
                    "period_id": self.period.id,
                    "date_from": date(2026, 4, 1),
                    "date_to": date(2026, 4, 5),
                }
            )

    def test_schedule_report_lists_periods_with_balance(self):
        self._create_vacation(date(2026, 4, 1), date(2026, 4, 30))
        wizard = self.env["hr.employee.vacation.schedule.wizard"].create({})
        self.assertNotIn(self.period, wizard._get_periods())
        wizard.only_with_balance = False
        wizard.employee_ids = self.employee
        self.assertEqual(wizard._get_periods(), self.period)
        action = wizard.with_context(discard_logo_check=True).action_print()
        self.assertEqual(
            action["report_name"], "hr_employee_vacation_log.report_vacation_schedule"
        )
        html = self.env["ir.actions.report"]._render_qweb_html(
            "hr_employee_vacation_log.action_report_vacation_schedule", self.period.ids
        )[0]
        self.assertIn(self.employee.name, html.decode())
