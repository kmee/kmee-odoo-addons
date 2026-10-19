from odoo.tests.common import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestTechLead(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        Users = cls.env["res.users"]
        group_user = cls.env.ref("base.group_user")
        cls.lead = Users.create(
            {
                "name": "Lead One",
                "login": "tech_lead_one",
                "email": "tech_lead_one@example.com",
                "groups_id": [(6, 0, [group_user.id])],
            }
        )
        cls.lead2 = Users.create(
            {
                "name": "Lead Two",
                "login": "tech_lead_two",
                "email": "tech_lead_two@example.com",
                "groups_id": [(6, 0, [group_user.id])],
            }
        )
        cls.project = cls.env["project.project"].create(
            {"name": "With lead", "tech_lead_id": cls.lead.id}
        )
        cls.project_nolead = cls.env["project.project"].create({"name": "No lead"})

    def test_task_inherits_project_tech_lead_on_form(self):
        """Given a project with a tech lead, When choosing it on a new task,
        Then the task tech lead is the project's."""
        form = Form(self.env["project.task"])
        form.name = "T"
        form.project_id = self.project
        self.assertEqual(form.save().tech_lead_id, self.lead)

    def test_changing_project_updates_tech_lead(self):
        """Given a task of a project with lead, When moved to a project without
        lead, Then the lead is cleared; moving back restores it."""
        with Form(self.env["project.task"]) as form:
            form.name = "T"
            form.project_id = self.project
            self.assertEqual(form.tech_lead_id, self.lead)
            form.project_id = self.project_nolead
            self.assertFalse(form.tech_lead_id)
            form.project_id = self.project
            self.assertEqual(form.tech_lead_id, self.lead)

    def test_project_without_lead_gives_task_without_lead(self):
        """Given a project with no lead, Then a new task has no lead."""
        form = Form(self.env["project.task"])
        form.name = "T"
        form.project_id = self.project_nolead
        self.assertFalse(form.save().tech_lead_id)

    def test_task_lead_can_differ_from_project_lead(self):
        """Given a task, When its lead is set explicitly, Then the explicit
        value is stored independently of the project lead."""
        task = self.env["project.task"].create(
            {
                "name": "T",
                "project_id": self.project.id,
                "tech_lead_id": self.lead2.id,
            }
        )
        self.assertEqual(task.tech_lead_id, self.lead2)
        self.assertEqual(task.project_id.tech_lead_id, self.lead)

    def test_project_lead_change_does_not_rewrite_existing_tasks(self):
        """Given an existing task, When the project lead changes, Then the
        existing task keeps its lead (only new/moved tasks follow)."""
        task = self.env["project.task"].create(
            {
                "name": "T",
                "project_id": self.project.id,
                "tech_lead_id": self.lead.id,
            }
        )
        self.project.tech_lead_id = self.lead2
        self.assertEqual(task.tech_lead_id, self.lead)

    def test_group_tasks_by_tech_lead(self):
        """Given tasks with different leads, When grouping by tech lead,
        Then one group per lead."""
        Task = self.env["project.task"]
        Task.create(
            {"name": "A", "project_id": self.project.id, "tech_lead_id": self.lead.id}
        )
        Task.create(
            {"name": "B", "project_id": self.project.id, "tech_lead_id": self.lead2.id}
        )
        groups = Task.read_group(
            [("project_id", "=", self.project.id)],
            ["tech_lead_id"],
            ["tech_lead_id"],
        )
        self.assertEqual(len(groups), 2)

    def test_views_expose_tech_lead(self):
        """Project and task forms and the task search expose the tech lead."""
        proj = self.env["project.project"].get_view(
            self.env.ref("project.edit_project").id, "form"
        )
        self.assertIn("tech_lead_id", proj["arch"])
        task = self.env["project.task"].get_view(
            self.env.ref("project.view_task_form2").id, "form"
        )
        self.assertIn("tech_lead_id", task["arch"])
        search = self.env["project.task"].get_view(
            self.env.ref("project.view_task_search_form").id, "search"
        )
        self.assertIn("group_tech_lead", search["arch"])
