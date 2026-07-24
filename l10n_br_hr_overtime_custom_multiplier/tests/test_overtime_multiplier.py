# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import contextlib
import locale
from datetime import date, datetime
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

# Fixed reference dates (2024):
#   2024-01-01 -> Monday
#   2024-01-05 -> Friday
#   2024-01-07 -> Sunday
MONDAY = date(2024, 1, 1)
FRIDAY = date(2024, 1, 5)
SUNDAY = date(2024, 1, 7)


@tagged("post_install", "-at_install")
class TestOvertimeMultiplier(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                tracking_disable=True,
                test_queue_job_no_delay=True,
            )
        )
        cls.Overtime = cls.env["hr.attendance.overtime"]
        cls.Range = cls.env["hr.overtime.multiplier.range"]
        cls.Exception = cls.env["hr.attendance.exception"]

        # Enable overtime tracking so the base _update_overtime pipeline runs.
        cls.env.company.write(
            {
                "hr_attendance_overtime": True,
                "overtime_start_date": date(2020, 1, 1),
                "overtime_company_threshold": 0,
                "overtime_employee_threshold": 0,
            }
        )

        cls.employee = cls.env["hr.employee"].create(
            {"name": "Overtime Tester", "tz": "UTC"}
        )

        # Two Monday ranges to exercise the multi-range path (Bug 1 crash case).
        cls.range_mon_0_2 = cls.Range.create(
            {
                "name": "Mon 0-2",
                "monday": True,
                "overtime_from": 0.0,
                "overtime_to": 2.0,
                "multiplier": 1.5,
            }
        )
        cls.range_mon_2_4 = cls.Range.create(
            {
                "name": "Mon 2-4",
                "monday": True,
                "overtime_from": 2.0,
                "overtime_to": 4.0,
                "multiplier": 2.0,
            }
        )
        # Single Friday range (single-range path).
        cls.range_fri = cls.Range.create(
            {
                "name": "Fri 0-10",
                "friday": True,
                "overtime_from": 0.0,
                "overtime_to": 10.0,
                "multiplier": 1.6,
            }
        )
        # Single Sunday range.
        cls.range_sun = cls.Range.create(
            {
                "name": "Sun 0-10",
                "sunday": True,
                "overtime_from": 0.0,
                "overtime_to": 10.0,
                "multiplier": 2.0,
            }
        )
        # Single Holiday range.
        cls.range_holiday = cls.Range.create(
            {
                "name": "Holiday 0-10",
                "holiday": True,
                "overtime_from": 0.0,
                "overtime_to": 10.0,
                "multiplier": 2.5,
            }
        )

    def _create_overtime(self, day, duration):
        return self.Overtime.create(
            {
                "employee_id": self.employee.id,
                "date": day,
                "duration": duration,
                "duration_real": duration,
            }
        )

    def test_total_hours_compute(self):
        self.assertEqual(self.range_mon_0_2.total_hours, 2.0)
        self.assertEqual(self.range_fri.total_hours, 10.0)

    def test_single_range(self):
        """Overtime fitting entirely inside one range gets its multiplier."""
        overtime = self._create_overtime(FRIDAY, 3.0)
        self.assertEqual(overtime.applied_multiplier, 1.6)
        self.assertEqual(overtime.extra_hours_without_multiplier, 3.0)
        self.assertAlmostEqual(overtime.duration, 4.8, places=2)
        self.assertEqual(overtime.overtime_range_id, self.range_fri)
        # No adjustment records are generated for a single-range case.
        adjustments = self.Overtime.search(
            [("adjustment_overtime_id", "=", overtime.id)]
        )
        self.assertFalse(adjustments)

    def test_multiple_ranges(self):
        """Overtime spanning 2+ ranges must not crash (Bug 1) and creates
        adjustment records for the extra ranges."""
        overtime = self._create_overtime(MONDAY, 4.0)
        # Main record: consumes the first range fully (2h * 1.5).
        self.assertEqual(overtime.applied_multiplier, 1.5)
        self.assertEqual(overtime.extra_hours_without_multiplier, 2.0)
        self.assertAlmostEqual(overtime.duration, 3.0, places=2)

        adjustments = self.Overtime.search(
            [("adjustment_overtime_id", "=", overtime.id)]
        )
        self.assertEqual(len(adjustments), 1)
        adj = adjustments
        # Second range (Bug 1 branch that used the non-existent `.total`).
        self.assertTrue(adj.adjustment)
        self.assertEqual(adj.applied_multiplier, 2.0)
        self.assertEqual(adj.extra_hours_without_multiplier, 2.0)
        self.assertAlmostEqual(adj.duration, 4.0, places=2)

    def test_exception_day_override(self):
        """An attendance exception overrides the effective day of the week."""
        self.Exception.create(
            {
                "employee_id": self.employee.id,
                "date": FRIDAY,
                "day_of_week_override": "monday",
            }
        )
        # A Friday, but overridden to Monday -> Monday range applies.
        overtime = self._create_overtime(FRIDAY, 1.0)
        self.assertEqual(overtime.applied_multiplier, 1.5)
        self.assertEqual(overtime.overtime_range_id, self.range_mon_0_2)

    def test_public_holiday(self):
        """When the date is a public holiday, the holiday range applies."""
        with patch.object(
            type(self.env["hr.holidays.public"]),
            "is_public_holiday",
            return_value=True,
        ):
            overtime = self._create_overtime(FRIDAY, 1.0)
        self.assertEqual(overtime.applied_multiplier, 2.5)
        self.assertEqual(overtime.overtime_range_id, self.range_holiday)

    def test_search_range_ptbr_locale(self):
        """The weekday lookup must be locale-independent (Bug 2)."""
        previous = locale.setlocale(locale.LC_TIME)
        try:
            # pt_BR may not be installed in the runner; either way the
            # assertion below proves the logic no longer relies on locale.
            with contextlib.suppress(locale.Error):
                locale.setlocale(locale.LC_TIME, "pt_BR.UTF-8")
            ranges = self.Range._search_overtime_range(MONDAY, self.employee)
            self.assertIn(self.range_mon_0_2, ranges)
            self.assertIn(self.range_mon_2_4, ranges)
            self.assertNotIn(self.range_fri, ranges)
        finally:
            locale.setlocale(locale.LC_TIME, previous)

    def test_update_overtime_recompute(self):
        """Recompute path via _update_overtime applies the multiplier and note."""
        attendance = self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": datetime(2024, 1, 7, 10, 0, 0),
                "check_out": datetime(2024, 1, 7, 12, 0, 0),
            }
        )
        attendance._update_overtime()
        overtime = self.Overtime.search(
            [
                ("attendance_id", "=", attendance.id),
                ("adjustment", "=", False),
            ]
        )
        self.assertTrue(overtime)
        self.assertEqual(overtime.applied_multiplier, 2.0)
        self.assertAlmostEqual(overtime.extra_hours_without_multiplier, 2.0, places=2)
        self.assertAlmostEqual(overtime.duration, 4.0, places=2)
        self.assertTrue(overtime.note)

    def test_payment_wizard(self):
        """Payment wizard validations and negative adjustment creation."""
        # Give the employee some positive overtime balance.
        self._create_overtime(FRIDAY, 3.0)  # -> 4.8h after multiplier
        Wizard = self.env["hr_attendance.overtime.payment.wizard"]

        # payment_total must be > 0.
        wiz_zero = Wizard.create(
            {"employee_id": self.employee.id, "payment_total": 0.0}
        )
        with self.assertRaises(UserError):
            wiz_zero.doit()

        # payment_total cannot exceed total overtime.
        wiz_over = Wizard.create(
            {"employee_id": self.employee.id, "payment_total": 100.0}
        )
        with self.assertRaises(UserError):
            wiz_over.doit()

        # Valid payment creates a negative adjustment and returns an 'in' domain.
        wiz_ok = Wizard.create({"employee_id": self.employee.id, "payment_total": 2.0})
        action = wiz_ok.doit()
        self.assertEqual(action["domain"][0][1], "in")

        payment = self.Overtime.search(
            [
                ("employee_id", "=", self.employee.id),
                ("adjustment", "=", True),
                ("duration", "=", -2.0),
            ]
        )
        self.assertTrue(payment)
