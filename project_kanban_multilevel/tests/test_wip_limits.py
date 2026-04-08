from odoo.tests.common import TransactionCase


class TestWipLimits(TransactionCase):

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
                "wip_limit": 3,
                "wip_limit_type": "count",
                "area_type": "progress",
                "project_ids": [(4, cls.project.id)],
            }
        )
        cls.stage_backlog = cls.env["project.task.type"].create(
            {
                "name": "Backlog",
                "wip_limit": 0,
                "area_type": "requested",
                "project_ids": [(4, cls.project.id)],
            }
        )
        cls.stage_qa = cls.env["project.task.type"].create(
            {
                "name": "QA",
                "wip_limit": 10,
                "wip_limit_type": "size",
                "area_type": "progress",
                "project_ids": [(4, cls.project.id)],
            }
        )

    def test_wip_count_violation_logs_message(self):
        """Moving a task to exceed WIP should succeed but log a message."""
        tasks = self.env["project.task"]
        for i in range(3):
            tasks += self.env["project.task"].create(
                {
                    "name": f"Task {i}",
                    "project_id": self.project.id,
                    "stage_id": self.stage_dev.id,
                }
            )
        # Create one more in backlog and move it
        new_task = self.env["project.task"].create(
            {
                "name": "Task overflow",
                "project_id": self.project.id,
                "stage_id": self.stage_backlog.id,
            }
        )
        # This should NOT raise, WIP is soft
        new_task.write({"stage_id": self.stage_dev.id})
        self.assertEqual(new_task.stage_id, self.stage_dev)

        # Check that a message was posted
        messages = new_task.message_ids.filtered(
            lambda m: "WIP limit excedido" in (m.body or "")
        )
        self.assertTrue(messages, "WIP violation should log a chatter message")

    def test_wip_no_limit_no_message(self):
        """Stage with wip_limit=0 should not produce violation messages."""
        task = self.env["project.task"].create(
            {
                "name": "Task backlog",
                "project_id": self.project.id,
                "stage_id": self.stage_dev.id,
            }
        )
        task.write({"stage_id": self.stage_backlog.id})
        messages = task.message_ids.filtered(
            lambda m: "WIP limit excedido" in (m.body or "")
        )
        self.assertFalse(messages)

    def test_wip_by_size(self):
        """WIP by size sums card_size instead of counting tasks."""
        self.env["project.task"].create(
            {
                "name": "Big task",
                "project_id": self.project.id,
                "stage_id": self.stage_qa.id,
                "card_size": 8,
            }
        )
        # Create another task in backlog with size 5 and move to QA
        task2 = self.env["project.task"].create(
            {
                "name": "Another big task",
                "project_id": self.project.id,
                "stage_id": self.stage_backlog.id,
                "card_size": 5,
            }
        )
        task2.write({"stage_id": self.stage_qa.id})
        # Total = 13 > 10, should have violation message
        messages = task2.message_ids.filtered(
            lambda m: "WIP limit excedido" in (m.body or "")
        )
        self.assertTrue(messages)

    def test_wip_soft_enforcement(self):
        """Moving task to WIP-exceeded column must succeed (soft limit)."""
        for i in range(4):
            self.env["project.task"].create(
                {
                    "name": f"Fill task {i}",
                    "project_id": self.project.id,
                    "stage_id": self.stage_dev.id,
                }
            )
        # Move yet another — should work
        overflow = self.env["project.task"].create(
            {
                "name": "Overflow",
                "project_id": self.project.id,
                "stage_id": self.stage_backlog.id,
            }
        )
        overflow.write({"stage_id": self.stage_dev.id})
        self.assertEqual(overflow.stage_id, self.stage_dev)
