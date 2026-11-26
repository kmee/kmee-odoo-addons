# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase


class TestHrEmployeeSalaryHistory(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create(
            {"name": "Funcionário", "current_salary": 3000.0}
        )

    def _adjust(self, salary, reason="Dissídio coletivo"):
        action = self.employee.action_adjust_salary()
        wizard = (
            self.env[action["res_model"]]
            .with_context(**action["context"])
            .create({"reason": reason, "salary": salary})
        )
        wizard.action_confirm()

    def test_wizard_updates_salary_and_keeps_history(self):
        self._adjust(3300.0)
        self.assertEqual(self.employee.current_salary, 3300.0)
        history = self.employee.salary_history_ids
        self.assertEqual(len(history), 1)
        self.assertEqual(history.previous_salary, 3000.0)
        self.assertEqual(history.salary, 3300.0)
        self.assertEqual(history.reason, "Dissídio coletivo")
        self.assertAlmostEqual(history.increase_percentage, 10.0)

    def test_successive_adjustments_chain_the_previous_salary(self):
        self._adjust(3300.0)
        self._adjust(3465.0, reason="Mérito")
        latest = self.env["hr.employee.salary.history"].search(
            [("employee_id", "=", self.employee.id)], limit=1
        )
        self.assertEqual(latest.previous_salary, 3300.0)
        self.assertAlmostEqual(latest.increase_percentage, 5.0)
