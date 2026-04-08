from datetime import datetime, timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestAnalytics(TransactionCase):
    """F10 — Analytics: lead time, cycle time."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env["project.project"].create(
            {"name": "Analytics Project", "use_multilevel_kanban": True}
        )
        cls.stage_backlog = cls.env["project.task.type"].create(
            {
                "name": "Backlog",
                "area_type": "requested",
                "project_ids": [(4, cls.project.id)],
            }
        )
        cls.stage_dev = cls.env["project.task.type"].create(
            {
                "name": "Dev",
                "area_type": "progress",
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

    def test_date_in_progress_set_on_first_progress(self):
        task = self.env["project.task"].create(
            {
                "name": "Task",
                "project_id": self.project.id,
                "stage_id": self.stage_backlog.id,
            }
        )
        self.assertFalse(task.date_in_progress)
        task.write({"stage_id": self.stage_dev.id})
        self.assertTrue(task.date_in_progress)

    def test_date_in_progress_not_overwritten(self):
        task = self.env["project.task"].create(
            {
                "name": "Task",
                "project_id": self.project.id,
                "stage_id": self.stage_dev.id,
            }
        )
        first_date = task.date_in_progress
        self.assertTrue(first_date, "Should be set on creation in progress stage")
        # Move to backlog and back to dev — should keep first date
        task.write({"stage_id": self.stage_backlog.id})
        self.assertEqual(task.date_in_progress, first_date,
                         "date_in_progress should be preserved when leaving progress")
        task.write({"stage_id": self.stage_dev.id})
        self.assertEqual(task.date_in_progress, first_date,
                         "date_in_progress should not be overwritten on re-entry")

    def test_date_done_set_on_done_stage(self):
        task = self.env["project.task"].create(
            {
                "name": "Task",
                "project_id": self.project.id,
                "stage_id": self.stage_dev.id,
            }
        )
        self.assertFalse(task.date_done)
        task.write({"stage_id": self.stage_done.id})
        self.assertTrue(task.date_done)

    def test_date_done_cleared_on_move_back(self):
        task = self.env["project.task"].create(
            {
                "name": "Task",
                "project_id": self.project.id,
                "stage_id": self.stage_done.id,
            }
        )
        self.assertTrue(task.date_done)
        task.write({"stage_id": self.stage_dev.id})
        self.assertFalse(task.date_done)

    def test_lead_time_computed(self):
        task = self.env["project.task"].create(
            {
                "name": "Task",
                "project_id": self.project.id,
                "stage_id": self.stage_dev.id,
            }
        )
        # Backdate create_date to 3 days ago for meaningful lead time
        three_days_ago = datetime.now() - timedelta(days=3)
        self.env.cr.execute(
            "UPDATE project_task SET create_date = %s WHERE id = %s",
            (three_days_ago, task.id),
        )
        task.invalidate_recordset(["create_date"])
        task.write({"stage_id": self.stage_done.id})
        self.assertGreaterEqual(task.lead_time_days, 2)

    def test_cycle_time_computed(self):
        task = self.env["project.task"].create(
            {
                "name": "Task",
                "project_id": self.project.id,
                "stage_id": self.stage_dev.id,
            }
        )
        # Has date_in_progress from creation in progress stage
        task.write({"stage_id": self.stage_done.id})
        self.assertGreaterEqual(task.cycle_time_days, 0)


class TestWizards(TransactionCase):
    """F09 — Swimlane wizards."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env["project.project"].create(
            {"name": "Wizard Project", "use_multilevel_kanban": True}
        )

    def test_template_standard_creates_4_swimlanes(self):
        wizard = self.env["project.kanban.swimlane.wizard"].create(
            {
                "project_id": self.project.id,
                "template": "standard",
            }
        )
        wizard.action_apply()
        swimlanes = self.env["project.kanban.swimlane"].search(
            [("project_id", "=", self.project.id)]
        )
        self.assertEqual(len(swimlanes), 4)
        names = swimlanes.mapped("name")
        self.assertIn("Features", names)
        self.assertIn("Expedite", names)

    def test_template_minimal_creates_2_swimlanes(self):
        project2 = self.env["project.project"].create(
            {"name": "Minimal Project", "use_multilevel_kanban": True}
        )
        wizard = self.env["project.kanban.swimlane.wizard"].create(
            {
                "project_id": project2.id,
                "template": "minimal",
            }
        )
        wizard.action_apply()
        swimlanes = self.env["project.kanban.swimlane"].search(
            [("project_id", "=", project2.id)]
        )
        self.assertEqual(len(swimlanes), 2)

    def test_copy_swimlanes(self):
        # Setup source project with swimlanes
        source = self.env["project.project"].create(
            {"name": "Source", "use_multilevel_kanban": True}
        )
        self.env["project.kanban.swimlane"].create(
            {"name": "Lane A", "project_id": source.id, "color": "#111111"}
        )
        self.env["project.kanban.swimlane"].create(
            {"name": "Lane B", "project_id": source.id, "color": "#222222"}
        )
        # Target project
        target = self.env["project.project"].create(
            {"name": "Target", "use_multilevel_kanban": True}
        )
        wizard = self.env["project.kanban.copy.swimlanes.wizard"].create(
            {
                "source_project_id": source.id,
                "target_project_id": target.id,
            }
        )
        wizard.action_copy()
        target_lanes = self.env["project.kanban.swimlane"].search(
            [("project_id", "=", target.id)]
        )
        self.assertEqual(len(target_lanes), 2)
        self.assertEqual(
            set(target_lanes.mapped("name")), {"Lane A", "Lane B"}
        )

    def test_aging_threshold_default(self):
        self.assertEqual(self.project.aging_threshold, 5)
        self.project.aging_threshold = 10
        self.assertEqual(self.project.aging_threshold, 10)


class TestPortfolio(TransactionCase):
    """F11 — Portfolio."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project1 = cls.env["project.project"].create({"name": "P1"})
        cls.project2 = cls.env["project.project"].create({"name": "P2"})

    def test_portfolio_creation(self):
        portfolio = self.env["project.portfolio"].create(
            {
                "name": "Digital Products",
                "project_ids": [
                    (6, 0, [self.project1.id, self.project2.id])
                ],
            }
        )
        self.assertEqual(portfolio.project_count, 2)

    def test_portfolio_task_count(self):
        stage = self.env["project.task.type"].create(
            {"name": "Todo", "project_ids": [(4, self.project1.id)]}
        )
        for i in range(3):
            self.env["project.task"].create(
                {
                    "name": f"Task {i}",
                    "project_id": self.project1.id,
                    "stage_id": stage.id,
                }
            )
        portfolio = self.env["project.portfolio"].create(
            {
                "name": "Test Portfolio",
                "project_ids": [(6, 0, [self.project1.id])],
            }
        )
        self.assertEqual(portfolio.task_count, 3)

    def test_portfolio_action_open_projects(self):
        portfolio = self.env["project.portfolio"].create(
            {
                "name": "Test",
                "project_ids": [
                    (6, 0, [self.project1.id, self.project2.id])
                ],
            }
        )
        action = portfolio.action_open_projects()
        self.assertEqual(action["res_model"], "project.project")

    def test_project_portfolio_link(self):
        portfolio = self.env["project.portfolio"].create(
            {"name": "Test Portfolio"}
        )
        self.project1.portfolio_id = portfolio.id
        self.assertEqual(self.project1.portfolio_id, portfolio)
