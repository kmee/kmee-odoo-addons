# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAllocationPlan(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.company
        cls.employee = cls.env["hr.employee"].create(
            {"name": "Plan Employee", "company_id": cls.company.id}
        )
        cls.env["hr.contract"].create(
            {
                "name": "Contract",
                "employee_id": cls.employee.id,
                "wage": 1000.0,
                "date_start": "2020-01-01",
                "state": "open",
            }
        )
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Plan Leave",
                "requires_allocation": "yes",
                "employee_requests": "no",
                "allocation_validation_type": "officer",
            }
        )

    def _plan(self, **vals):
        values = {
            "name": "Plan",
            "holiday_status_id": self.leave_type.id,
            "holiday_type": "company",
            "allocation_type": "regular",
            "number_of_days": 5,
        }
        values.update(vals)
        return self.env["hr.leave.allocation.plan"].create(values)

    def test_computed_defaults(self):
        plan = self._plan()
        self.assertEqual(plan.state, "draft")
        self.assertEqual(plan.mode_company_id, self.company)
        self.assertFalse(plan.department_id)

    def test_recompute_selects_employees(self):
        plan = self._plan()
        plan.action_recompute_plan()
        self.assertEqual(plan.state, "check")
        self.assertIn(self.employee, plan.plan_employee_ids)

    def test_run_regular_creates_allocation(self):
        plan = self._plan()
        plan.plan_employee_ids = self.employee
        plan.action_run_update()
        self.assertEqual(plan.state, "draft")
        allocations = plan.allocation_ids.filtered(
            lambda a: a.employee_id == self.employee
        )
        self.assertTrue(allocations)
        self.assertEqual(allocations[0].number_of_days, 5)

    def test_cancel_and_back_to_draft(self):
        plan = self._plan()
        plan.action_cancel()
        self.assertEqual(plan.state, "cancel")
        plan.action_back2draft()
        self.assertEqual(plan.state, "draft")

    def test_back_to_draft_removes_allocations(self):
        plan = self._plan()
        plan.plan_employee_ids = self.employee
        plan.action_run_update()
        self.assertTrue(plan.allocation_ids)
        plan.action_cancel()
        plan.action_back2draft()
        self.assertEqual(plan.state, "draft")
        self.assertFalse(plan.allocation_ids)
