from odoo.tests.common import TransactionCase


class TestCompatibility(TransactionCase):
    """Cenários de compatibilidade e regressão."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stage = cls.env["project.task.type"].create(
            {"name": "Backlog", "area_type": "requested"}
        )

    def test_project_without_multilevel_works(self):
        """COMPAT_S01: Projeto sem multilevel não é afetado."""
        project = self.env["project.project"].create(
            {
                "name": "Normal Project",
                "use_multilevel_kanban": False,
            }
        )
        self.assertFalse(project.use_multilevel_kanban)
        # Can still create tasks normally
        task = self.env["project.task"].create(
            {
                "name": "Normal task",
                "project_id": project.id,
                "stage_id": self.stage.id,
            }
        )
        self.assertTrue(task.id)
        self.assertEqual(task.sub_stage, "doing")
        self.assertFalse(task.swimlane_id)

    def test_task_without_swimlane(self):
        """COMPAT_S02: Task criada via API sem swimlane funciona."""
        project = self.env["project.project"].create(
            {
                "name": "Multilevel Project",
                "use_multilevel_kanban": True,
            }
        )
        task = self.env["project.task"].create(
            {
                "name": "API task",
                "project_id": project.id,
                "stage_id": self.stage.id,
            }
        )
        self.assertFalse(task.swimlane_id)
        self.assertEqual(task.sub_stage, "doing")
        self.assertEqual(task.card_size, 1)

    def test_native_subtasks_still_work(self):
        """COMPAT_S03: Subtarefas nativas continuam funcionando."""
        project = self.env["project.project"].create(
            {
                "name": "Test Project",
                "use_multilevel_kanban": True,
            }
        )
        parent = self.env["project.task"].create(
            {
                "name": "Parent",
                "project_id": project.id,
                "stage_id": self.stage.id,
            }
        )
        child = self.env["project.task"].create(
            {
                "name": "Child",
                "project_id": project.id,
                "stage_id": self.stage.id,
                "parent_id": parent.id,
            }
        )
        self.assertEqual(child.parent_id, parent)
        parent.invalidate_recordset(["child_ids"])
        self.assertIn(child, parent.child_ids)

    def test_existing_project_activate_multilevel(self):
        """COMPAT_S04: Ativar multilevel em projeto existente preserva dados."""
        project = self.env["project.project"].create(
            {
                "name": "Existing",
                "use_multilevel_kanban": False,
            }
        )
        tasks = self.env["project.task"]
        for i in range(5):
            tasks += self.env["project.task"].create(
                {
                    "name": f"Task {i}",
                    "project_id": project.id,
                    "stage_id": self.stage.id,
                }
            )
        # Activate multilevel
        project.write({"use_multilevel_kanban": True})
        self.assertTrue(project.use_multilevel_kanban)
        # All tasks still exist and have no swimlane
        for task in tasks:
            self.assertFalse(task.swimlane_id)
            self.assertTrue(task.name)

    def test_swimlane_project_isolation(self):
        """Swimlanes are isolated per project."""
        p1 = self.env["project.project"].create(
            {"name": "P1", "use_multilevel_kanban": True}
        )
        p2 = self.env["project.project"].create(
            {"name": "P2", "use_multilevel_kanban": True}
        )
        sw1 = self.env["project.kanban.swimlane"].create(
            {"name": "Features", "project_id": p1.id}
        )
        sw2 = self.env["project.kanban.swimlane"].create(
            {"name": "Features", "project_id": p2.id}
        )
        # Same name, different projects — both exist
        self.assertNotEqual(sw1.id, sw2.id)
        self.assertEqual(sw1.name, sw2.name)
