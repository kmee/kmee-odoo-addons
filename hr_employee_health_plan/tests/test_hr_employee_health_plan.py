# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase


class TestHrEmployeeHealthPlan(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({"name": "Funcionário"})

    def test_employee_has_health_and_dental_plans(self):
        self.employee.health_plan_ids = [
            (0, 0, {"operator": "Operadora A", "amount": 350.0}),
            (0, 0, {"plan_type": "dental", "operator": "Operadora B", "amount": 40.0}),
        ]
        plans = self.employee.health_plan_ids
        self.assertCountEqual(plans.mapped("plan_type"), ["health", "dental"])
        self.assertEqual(plans.currency_id, self.employee.company_id.currency_id)

    def test_end_cannot_be_before_start(self):
        with self.assertRaises(ValidationError):
            self.env["hr.employee.health.plan"].create(
                {
                    "employee_id": self.employee.id,
                    "date_start": date(2026, 5, 1),
                    "date_end": date(2026, 4, 1),
                }
            )
