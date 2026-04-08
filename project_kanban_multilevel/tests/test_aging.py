from datetime import datetime, timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestAging(TransactionCase):
    """F07 — Aging (tempo no estágio)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env["project.project"].create(
            {
                "name": "Test Aging",
                "use_multilevel_kanban": True,
            }
        )
        cls.stage_dev = cls.env["project.task.type"].create(
            {
                "name": "Dev",
                "area_type": "progress",
                "has_sub_stages": True,
                "project_ids": [(4, cls.project.id)],
            }
        )
        cls.stage_done = cls.env["project.task.type"].create(
            {
                "name": "Done",
                "area_type": "done",
                "project_ids": [(4, cls.project.id)],
            }
        )

    def test_aging_days_computed(self):
        """F07_S03: aging_days reflects days since stage_entered_date."""
        task = self.env["project.task"].create(
            {
                "name": "Old task",
                "project_id": self.project.id,
                "stage_id": self.stage_dev.id,
            }
        )
        # Manually set to 7 days ago
        seven_days_ago = datetime.now() - timedelta(days=7)
        task.write({"stage_entered_date": seven_days_ago})
        task.invalidate_recordset(["aging_days"])
        task._compute_aging_days()
        self.assertGreaterEqual(task.aging_days, 6)
        self.assertLessEqual(task.aging_days, 8)

    def test_stage_change_resets_aging(self):
        """F07_S01: Changing stage updates stage_entered_date."""
        task = self.env["project.task"].create(
            {
                "name": "Task",
                "project_id": self.project.id,
                "stage_id": self.stage_dev.id,
            }
        )
        # Backdate
        old = datetime.now() - timedelta(days=10)
        task.write({"stage_entered_date": old})
        # Change stage — should reset stage_entered_date to now
        before = fields.Datetime.now()
        task.write({"stage_id": self.stage_done.id})
        self.assertGreaterEqual(task.stage_entered_date, before)

    def test_sub_stage_change_resets_aging(self):
        """F07_S02: Changing sub_stage updates stage_entered_date."""
        task = self.env["project.task"].create(
            {
                "name": "Task",
                "project_id": self.project.id,
                "stage_id": self.stage_dev.id,
                "sub_stage": "doing",
            }
        )
        old = datetime.now() - timedelta(days=5)
        task.write({"stage_entered_date": old})
        before = fields.Datetime.now()
        task.write({"sub_stage": "done"})
        self.assertGreaterEqual(task.stage_entered_date, before)

    def test_cron_recompute(self):
        """Cron method recomputes aging for all tasks."""
        task = self.env["project.task"].create(
            {
                "name": "Cron test",
                "project_id": self.project.id,
                "stage_id": self.stage_dev.id,
            }
        )
        three_days_ago = datetime.now() - timedelta(days=3)
        task.write({"stage_entered_date": three_days_ago})
        # Run cron
        self.env["project.task"]._cron_recompute_aging()
        task.invalidate_recordset(["aging_days"])
        self.assertGreaterEqual(task.aging_days, 2)
