from datetime import datetime, timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestTask(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env["project.project"].create(
            {
                "name": "Test Project",
                "use_multilevel_kanban": True,
            }
        )
        cls.stage_dev = cls.env["project.task.type"].create(
            {
                "name": "Desenvolvimento",
                "has_sub_stages": True,
                "wip_limit": 8,
                "area_type": "progress",
                "project_ids": [(4, cls.project.id)],
            }
        )
        cls.stage_review = cls.env["project.task.type"].create(
            {
                "name": "Code Review",
                "has_sub_stages": True,
                "wip_limit": 4,
                "area_type": "progress",
                "project_ids": [(4, cls.project.id)],
            }
        )
        cls.stage_done = cls.env["project.task.type"].create(
            {
                "name": "Concluído",
                "area_type": "done",
                "project_ids": [(4, cls.project.id)],
            }
        )

    def test_sub_stage_default(self):
        task = self.env["project.task"].create(
            {
                "name": "Task 1",
                "project_id": self.project.id,
                "stage_id": self.stage_dev.id,
            }
        )
        self.assertEqual(task.sub_stage, "doing")

    def test_sub_stage_reset_on_stage_change(self):
        task = self.env["project.task"].create(
            {
                "name": "Task 1",
                "project_id": self.project.id,
                "stage_id": self.stage_dev.id,
                "sub_stage": "done",
            }
        )
        self.assertEqual(task.sub_stage, "done")
        task.write({"stage_id": self.stage_review.id})
        self.assertEqual(task.sub_stage, "doing")

    def test_stage_entered_date_on_create(self):
        before = fields.Datetime.now()
        task = self.env["project.task"].create(
            {
                "name": "Task 1",
                "project_id": self.project.id,
                "stage_id": self.stage_dev.id,
            }
        )
        self.assertTrue(task.stage_entered_date)
        self.assertGreaterEqual(task.stage_entered_date, before)

    def test_stage_entered_date_on_stage_change(self):
        task = self.env["project.task"].create(
            {
                "name": "Task 1",
                "project_id": self.project.id,
                "stage_id": self.stage_dev.id,
            }
        )
        old_date = task.stage_entered_date
        # Force a small delay
        task.write({"stage_id": self.stage_review.id})
        self.assertGreaterEqual(task.stage_entered_date, old_date)

    def test_stage_entered_date_on_sub_stage_change(self):
        task = self.env["project.task"].create(
            {
                "name": "Task 1",
                "project_id": self.project.id,
                "stage_id": self.stage_dev.id,
                "sub_stage": "doing",
            }
        )
        old_date = task.stage_entered_date
        task.write({"sub_stage": "done"})
        self.assertGreaterEqual(task.stage_entered_date, old_date)

    def test_aging_days(self):
        task = self.env["project.task"].create(
            {
                "name": "Task 1",
                "project_id": self.project.id,
                "stage_id": self.stage_dev.id,
            }
        )
        # Manually set stage_entered_date to 5 days ago
        five_days_ago = datetime.now() - timedelta(days=5)
        task.write({"stage_entered_date": five_days_ago})
        task.invalidate_recordset(["aging_days"])
        # Recompute
        task._compute_aging_days()
        self.assertGreaterEqual(task.aging_days, 4)  # Allow for timing
        self.assertLessEqual(task.aging_days, 6)

    def test_card_size_default(self):
        task = self.env["project.task"].create(
            {
                "name": "Task 1",
                "project_id": self.project.id,
                "stage_id": self.stage_dev.id,
            }
        )
        self.assertEqual(task.card_size, 1)

    def test_blocked_fields(self):
        task = self.env["project.task"].create(
            {
                "name": "Task 1",
                "project_id": self.project.id,
                "stage_id": self.stage_dev.id,
                "is_blocked": True,
                "blocked_reason": "Waiting for API key",
            }
        )
        self.assertTrue(task.is_blocked)
        self.assertEqual(task.blocked_reason, "Waiting for API key")
