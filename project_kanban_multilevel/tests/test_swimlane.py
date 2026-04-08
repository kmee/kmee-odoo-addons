from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestSwimlane(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env["project.project"].create(
            {
                "name": "Test Project",
                "use_multilevel_kanban": True,
            }
        )

    def test_create_swimlane(self):
        swimlane = self.env["project.kanban.swimlane"].create(
            {
                "name": "Features",
                "project_id": self.project.id,
                "color": "#714B67",
                "icon": "◆",
            }
        )
        self.assertEqual(swimlane.name, "Features")
        self.assertEqual(swimlane.sequence, 10)
        self.assertFalse(swimlane.is_expedite)
        self.assertFalse(swimlane.fold)

    def test_unique_constraint(self):
        self.env["project.kanban.swimlane"].create(
            {
                "name": "Bugs",
                "project_id": self.project.id,
            }
        )
        with self.assertRaises(Exception):
            self.env["project.kanban.swimlane"].create(
                {
                    "name": "Bugs",
                    "project_id": self.project.id,
                }
            )

    def test_task_count(self):
        swimlane = self.env["project.kanban.swimlane"].create(
            {
                "name": "Features",
                "project_id": self.project.id,
            }
        )
        stage = self.env["project.task.type"].create(
            {
                "name": "Backlog",
                "project_ids": [(4, self.project.id)],
            }
        )
        self.assertEqual(swimlane.task_count, 0)
        self.env["project.task"].create(
            {
                "name": "Task 1",
                "project_id": self.project.id,
                "stage_id": stage.id,
                "swimlane_id": swimlane.id,
            }
        )
        self.env["project.task"].create(
            {
                "name": "Task 2",
                "project_id": self.project.id,
                "stage_id": stage.id,
                "swimlane_id": swimlane.id,
            }
        )
        swimlane.invalidate_recordset()
        self.assertEqual(swimlane.task_count, 2)

    def test_ordering(self):
        sw1 = self.env["project.kanban.swimlane"].create(
            {
                "name": "Third",
                "project_id": self.project.id,
                "sequence": 30,
            }
        )
        sw2 = self.env["project.kanban.swimlane"].create(
            {
                "name": "First",
                "project_id": self.project.id,
                "sequence": 5,
            }
        )
        sw3 = self.env["project.kanban.swimlane"].create(
            {
                "name": "Second",
                "project_id": self.project.id,
                "sequence": 10,
            }
        )
        swimlanes = self.env["project.kanban.swimlane"].search(
            [("project_id", "=", self.project.id)],
            order="sequence, id",
        )
        self.assertEqual(swimlanes[0], sw2)
        self.assertEqual(swimlanes[1], sw3)
        self.assertEqual(swimlanes[2], sw1)
