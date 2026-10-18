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
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Tagged leave",
                "requires_allocation": "yes",
                "employee_requests": "no",
                "allocation_validation_type": "officer",
            }
        )

    def _allocation(self, holiday_type, tags):
        return self.env["hr.leave.allocation"].create(
            {
                "name": "Tag allocation",
                "holiday_status_id": self.leave_type.id,
                "holiday_type": holiday_type,
                "category_ids": [(6, 0, tags.ids)],
                "number_of_days": 5,
            }
        )

    def test_category_or_allocates_any_tag(self):
        allocation = self._allocation("category_or", self.tag_a | self.tag_b)
        allocation.action_validate()
        childs = self.env["hr.leave.allocation"].search(
            [("parent_id", "=", allocation.id)]
        )
        self.assertEqual(childs.employee_id, self.emp_1 | self.emp_2)

    def test_category_and_allocates_all_tags(self):
        allocation = self._allocation("category_and", self.tag_a | self.tag_b)
        allocation.action_validate()
        childs = self.env["hr.leave.allocation"].search(
            [("parent_id", "=", allocation.id)]
        )
        self.assertEqual(childs.employee_id, self.emp_2)
