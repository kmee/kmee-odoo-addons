# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAllocationTags(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(cls.env.context, tracking_disable=True, mail_notrack=True)
        )
        cls.tag_a = cls.env["hr.employee.category"].create({"name": "Tag A"})
        cls.tag_b = cls.env["hr.employee.category"].create({"name": "Tag B"})
        cls.emp_1 = cls.env["hr.employee"].create(
            {"name": "Emp 1", "category_ids": [(6, 0, cls.tag_a.ids)]}
        )
        cls.emp_2 = cls.env["hr.employee"].create(
            {"name": "Emp 2", "category_ids": [(6, 0, (cls.tag_a | cls.tag_b).ids)]}
        )
        cls.work_entry_type = cls.env["hr.work.entry.type"].create(
            {
                "name": "Tagged leave",
                "code": "TAGGED",
                "requires_allocation": True,
                "employee_requests": False,
                "allocation_validation_type": "hr",
            }
        )

    def _wizard(self, mode, tags):
        return self.env["hr.leave.allocation.generate.multi.wizard"].create(
            {
                "name": "Tag allocation",
                "work_entry_type_id": self.work_entry_type.id,
                "category_mode": mode,
                "category_ids": [(6, 0, tags.ids)],
                "duration": 5,
            }
        )

    def _employees(self, wizard):
        return self.env["hr.employee"].search(wizard._get_employee_domain())

    def test_category_any_matches_any_tag(self):
        wizard = self._wizard("any", self.tag_b)
        self.assertEqual(
            self._employees(wizard) & (self.emp_1 | self.emp_2), self.emp_2
        )
        wizard = self._wizard("any", self.tag_a | self.tag_b)
        self.assertEqual(
            self._employees(wizard) & (self.emp_1 | self.emp_2), self.emp_1 | self.emp_2
        )

    def test_category_all_matches_every_tag(self):
        wizard = self._wizard("all", self.tag_a | self.tag_b)
        self.assertEqual(
            self._employees(wizard) & (self.emp_1 | self.emp_2), self.emp_2
        )

    def test_generate_allocations_by_tags(self):
        wizard = self._wizard("all", self.tag_a | self.tag_b)
        action = wizard.action_generate_allocations()
        allocations = self.env["hr.leave.allocation"].search(action["domain"])
        self.assertEqual(allocations.employee_id, self.emp_2)

    def test_no_tags_keeps_standard_domain(self):
        wizard = self._wizard("any", self.env["hr.employee.category"])
        self.assertIn(self.emp_1, self._employees(wizard))
