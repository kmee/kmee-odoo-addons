from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProjectTaskServiceClass(TransactionCase):
    def test_service_class_on_task_and_report(self):
        service_class = self.env["project.task.service.class"].create(
            {"name": "Expedite", "color": 3}
        )
        project = self.env["project.project"].create({"name": "Project"})
        task = self.env["project.task"].create(
            {
                "name": "Task",
                "project_id": project.id,
                "service_class_id": service_class.id,
            }
        )
        task._onchange_service_class_id()
        self.assertEqual(task.color, 3)
        report = self.env["report.project.task.user"].search(
            [("service_class_id", "=", service_class.id)]
        )
        self.assertTrue(report)
