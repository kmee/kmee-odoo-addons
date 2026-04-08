import json

from odoo.tests.common import TransactionCase


class TestInitiatives(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env["project.project"].create(
            {
                "name": "Test Project",
                "use_multilevel_kanban": True,
            }
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
                "name": "Desenvolvimento",
                "has_sub_stages": True,
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

    def test_task_with_children_is_initiative(self):
        """F01_S01: Task sem parent com filhos é initiative."""
        parent = self.env["project.task"].create(
            {
                "name": "Portal v2",
                "project_id": self.project.id,
                "stage_id": self.stage_dev.id,
            }
        )
        self.assertFalse(parent.is_initiative)  # No children yet

        self.env["project.task"].create(
            {
                "name": "Child 1",
                "project_id": self.project.id,
                "stage_id": self.stage_backlog.id,
                "parent_id": parent.id,
            }
        )
        parent.invalidate_recordset(["is_initiative", "child_ids"])
        self.assertTrue(parent.is_initiative)

    def test_task_with_parent_not_initiative(self):
        """F01_S02: Task com parent não é initiative."""
        parent = self.env["project.task"].create(
            {
                "name": "Portal v2",
                "project_id": self.project.id,
                "stage_id": self.stage_dev.id,
            }
        )
        child = self.env["project.task"].create(
            {
                "name": "Subtarefa X",
                "project_id": self.project.id,
                "stage_id": self.stage_backlog.id,
                "parent_id": parent.id,
            }
        )
        self.assertFalse(child.is_initiative)

    def test_task_without_children_not_initiative(self):
        """F01_S03: Task folha sem filhos não é initiative."""
        task = self.env["project.task"].create(
            {
                "name": "Task isolada",
                "project_id": self.project.id,
                "stage_id": self.stage_backlog.id,
            }
        )
        self.assertFalse(task.is_initiative)

    def test_child_progress_data(self):
        """F01_S04: Mini-squares refletem estágio dos filhos."""
        parent = self.env["project.task"].create(
            {
                "name": "Portal v2",
                "project_id": self.project.id,
                "stage_id": self.stage_dev.id,
            }
        )
        self.env["project.task"].create(
            {
                "name": "Design",
                "project_id": self.project.id,
                "stage_id": self.stage_done.id,
                "parent_id": parent.id,
            }
        )
        self.env["project.task"].create(
            {
                "name": "API",
                "project_id": self.project.id,
                "stage_id": self.stage_dev.id,
                "parent_id": parent.id,
            }
        )
        self.env["project.task"].create(
            {
                "name": "Frontend",
                "project_id": self.project.id,
                "stage_id": self.stage_backlog.id,
                "parent_id": parent.id,
            }
        )
        self.env["project.task"].create(
            {
                "name": "Testes",
                "project_id": self.project.id,
                "stage_id": self.stage_backlog.id,
                "parent_id": parent.id,
            }
        )

        parent.invalidate_recordset(["child_progress_data"])
        data = json.loads(parent.child_progress_data)
        self.assertEqual(len(data), 4)

        area_types = [d["area_type"] for d in data]
        self.assertEqual(area_types.count("done"), 1)
        self.assertEqual(area_types.count("progress"), 1)
        self.assertEqual(area_types.count("requested"), 2)

    def test_initiative_recompute_on_child_add(self):
        """Initiative is detected when first child is added."""
        parent = self.env["project.task"].create(
            {
                "name": "Future Initiative",
                "project_id": self.project.id,
                "stage_id": self.stage_dev.id,
            }
        )
        self.assertFalse(parent.is_initiative)

        child = self.env["project.task"].create(
            {
                "name": "First child",
                "project_id": self.project.id,
                "stage_id": self.stage_backlog.id,
                "parent_id": parent.id,
            }
        )
        parent.invalidate_recordset(["is_initiative", "child_ids"])
        self.assertTrue(parent.is_initiative)

        # Remove parent from child
        child.write({"parent_id": False})
        parent.invalidate_recordset(["is_initiative", "child_ids"])
        self.assertFalse(parent.is_initiative)

    def test_empty_child_progress_data(self):
        """Tasks with no children return empty JSON array."""
        task = self.env["project.task"].create(
            {
                "name": "Solo task",
                "project_id": self.project.id,
                "stage_id": self.stage_backlog.id,
            }
        )
        data = json.loads(task.child_progress_data)
        self.assertEqual(data, [])
