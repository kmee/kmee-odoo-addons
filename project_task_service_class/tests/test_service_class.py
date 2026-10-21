from psycopg2 import IntegrityError

from odoo.tests import Form, TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestProjectTaskServiceClass(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.ServiceClass = cls.env["project.task.service.class"]
        cls.expedite = cls.ServiceClass.create({"name": "Expedite", "color": 3})
        cls.standard = cls.ServiceClass.create({"name": "Standard", "color": 5})
        cls.project = cls.env["project.project"].create({"name": "Project SC"})
        cls.user = cls.env["res.users"].create(
            {
                "name": "Project User",
                "login": "sc_project_user",
                "email": "sc_project_user@example.com",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref("project.group_project_user").id,
                        ],
                    )
                ],
            }
        )

    def _task(self, **vals):
        vals.setdefault("name", "Task")
        vals.setdefault("project_id", self.project.id)
        return self.env["project.task"].create(vals)

    def test_onchange_copies_color_to_task(self):
        """Given a service class with a color, When it is selected on the task
        form, Then the task color becomes the class color."""
        form = Form(self.env["project.task"])
        form.name = "Colored"
        form.project_id = self.project
        form.service_class_id = self.expedite
        self.assertEqual(form.save().color, 3)

    def test_onchange_switch_and_clear(self):
        """Given a colored task, When the class changes or is cleared, Then the
        color follows (cleared class resets color to 0)."""
        form = Form(self.env["project.task"])
        form.name = "Switch"
        form.project_id = self.project
        form.service_class_id = self.expedite
        self.assertEqual(form.save().color, 3)
        form.service_class_id = self.standard
        self.assertEqual(form.save().color, 5)
        form.service_class_id = self.env["project.task.service.class"]
        self.assertEqual(form.save().color, 0)

    def test_create_without_onchange_keeps_color(self):
        """Given a task created by code (no onchange), Then the explicit color
        is kept: the color sync is a UI behavior only."""
        task = self._task(service_class_id=self.expedite.id, color=7)
        self.assertEqual(task.color, 7)
        task._onchange_service_class_id()
        self.assertEqual(task.color, 3)

    def test_report_exposes_service_class(self):
        """Given tasks with classes, Then the task analysis report can filter
        and group by service class."""
        self._task(service_class_id=self.expedite.id)
        self._task(name="Other", service_class_id=self.standard.id)
        report = self.env["report.project.task.user"]
        found = report.search([("service_class_id", "=", self.expedite.id)])
        self.assertEqual(len(found), 1)
        groups = report.read_group(
            [("service_class_id", "in", (self.expedite | self.standard).ids)],
            ["service_class_id"],
            ["service_class_id"],
        )
        self.assertEqual(len(groups), 2)

    def test_task_group_by_service_class(self):
        """Given tasks of two classes, When grouping tasks by class, Then two
        groups appear."""
        self._task(service_class_id=self.expedite.id)
        self._task(service_class_id=self.standard.id)
        groups = self.env["project.task"].read_group(
            [("project_id", "=", self.project.id)],
            ["service_class_id"],
            ["service_class_id"],
        )
        self.assertEqual(len(groups), 2)

    def test_project_user_can_manage_service_classes(self):
        """Given an internal user (module ACL grants all internal users),
        Then they can create, edit and delete service classes."""
        sc = self.ServiceClass.with_user(self.user).create({"name": "By user"})
        sc.write({"color": 9})
        self.assertEqual(sc.color, 9)
        sc.unlink()
        self.assertFalse(sc.exists())

    def test_service_class_name_required(self):
        """A service class without name is rejected."""
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            with self.cr.savepoint():
                self.ServiceClass.create({"color": 1})

    def test_task_view_has_service_class(self):
        """The task form view exposes the service class field."""
        view = self.env["project.task"].get_view(
            self.env.ref("project.view_task_form2").id, "form"
        )
        self.assertIn("service_class_id", view["arch"])
