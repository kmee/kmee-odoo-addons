# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSaleOfDaysOff(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.employee = cls.env["hr.employee"].create({"name": "Abono Employee"})
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Vacation Abono",
                "requires_allocation": True,
                "employee_requests": False,
                "allocation_validation_type": "hr",
                "hr_holidays_sale_of_days_off": True,
            }
        )
        cls.allocation = cls.env["hr.leave.allocation"].create(
            {
                "name": "Vacation",
                "holiday_status_id": cls.leave_type.id,
                "employee_id": cls.employee.id,
                "number_of_days": 30,
                "date_from": "2020-01-01",
                "date_to": "2099-12-31",
            }
        )
        cls.allocation.action_approve()

    def _abono(self, days):
        return self.env["hr.leave.abono"].create(
            {
                "employee_id": self.employee.id,
                "holiday_allocation_id": self.allocation.id,
                "date": "2026-01-10",
                "days_sold": days,
            }
        )

    def test_confirm_sells_days(self):
        abono = self._abono(5)
        abono.action_confirm()
        self.assertEqual(abono.state, "paid")
        self.assertEqual(self.allocation.number_of_days_sold, 5)
        self.assertEqual(self.allocation.number_of_days, 25)
        self.assertEqual(self.allocation.days_off_sold_display, "5")

    def test_confirm_blocks_when_not_available(self):
        with self.assertRaises(ValidationError):
            self._abono(15).action_confirm()
        with self.assertRaises(ValidationError):
            self._abono(0).action_confirm()

    def test_unlink_restores_days(self):
        abono = self._abono(5)
        abono.action_confirm()
        abono.unlink()
        self.assertEqual(self.allocation.number_of_days_sold, 0)
        self.assertEqual(self.allocation.number_of_days, 30)

    def test_employee_display_and_action(self):
        self.assertEqual(self.employee.days_off_sold_display, "0")
        action = self.employee.action_sale_of_days_off()
        self.assertEqual(action["res_model"], "hr.leave.abono")
